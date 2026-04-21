"""Daily email report for FloodWatch job status."""
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .settings import EMAIL_CONFIG, DB_CONFIG
from .database import get_db_connection
from .logger_config import setup_logger

logger = setup_logger(__name__, 'email_report.log')


def _query_job_stats():
    """Query database for today's sync status."""
    stats = {}
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Multimodal: latest data_date and row count
            cursor.execute("""
                SELECT data_date, COUNT(*)
                FROM gha.multimodal_forecasts
                WHERE data_date >= CURRENT_DATE - INTERVAL '3 days'
                GROUP BY data_date
                ORDER BY data_date DESC
                LIMIT 5
            """)
            stats['multimodal'] = cursor.fetchall()

            # Google Flood: count and latest update
            cursor.execute("""
                SELECT COUNT(*), MAX(updated_at)::text
                FROM gha.google_flood_points_latest
            """)
            row = cursor.fetchone()
            stats['google_flood'] = {
                'count': row[0] if row else 0,
                'last_updated': row[1] if row else 'N/A',
            }

            # FloodProofs deterministic: latest dates
            try:
                cursor.execute("SAVEPOINT floodproofs_check")
                cursor.execute("""
                    SELECT data_date, feature_count
                    FROM gha.merged_deterministic_geojson
                    ORDER BY data_date DESC
                    LIMIT 3
                """)
                stats['floodproofs'] = cursor.fetchall()
                cursor.execute("RELEASE SAVEPOINT floodproofs_check")
            except Exception:
                cursor.execute("ROLLBACK TO SAVEPOINT floodproofs_check")
                stats['floodproofs'] = []

            # WRF: latest forecast date
            try:
                cursor.execute("SAVEPOINT wrf_check")
                cursor.execute("""
                    SELECT DISTINCT forecast_date
                    FROM wrf.daily_rainfall
                    ORDER BY forecast_date DESC
                    LIMIT 3
                """)
                stats['wrf'] = [r[0] for r in cursor.fetchall()]
                cursor.execute("RELEASE SAVEPOINT wrf_check")
            except Exception:
                cursor.execute("ROLLBACK TO SAVEPOINT wrf_check")
                stats['wrf'] = []

    except Exception as e:
        logger.error(f"Failed to query job stats: {e}")
        stats['error'] = str(e)

    return stats


def _parse_container_logs():
    """Parse recent log entries for job success/failure summary."""
    summary = {
        'multimodal': 'unknown',
        'floodproofs': 'unknown',
        'wrf': 'unknown',
        'google_flood': 'unknown',
        'db_backup': 'unknown',
    }

    try:
        import subprocess
        # Read last 500 lines of container logs (covers ~24h)
        result = subprocess.run(
            ['cat', '/proc/1/fd/1'],
            capture_output=True, text=True, timeout=5
        )
        # Fallback: just use what we can get from the log files
    except Exception:
        pass

    return summary


def _build_report_html(stats):
    """Build HTML email body from stats."""
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M EAT')

    # Multimodal section
    mm_rows = ''
    for data_date, count in (stats.get('multimodal') or []):
        mm_rows += f'<tr><td>{data_date}</td><td>{count:,}</td></tr>\n'
    if not mm_rows:
        mm_rows = '<tr><td colspan="2" style="color:red">No recent data</td></tr>'

    # Google Flood section
    gf = stats.get('google_flood', {})

    # FloodProofs section
    fp_rows = ''
    for data_date, fc in (stats.get('floodproofs') or []):
        fp_rows += f'<tr><td>{data_date}</td><td>{fc}</td></tr>\n'
    if not fp_rows:
        fp_rows = '<tr><td colspan="2" style="color:red">No recent data</td></tr>'

    # WRF section
    wrf_dates = ', '.join(str(d) for d in (stats.get('wrf') or []))
    if not wrf_dates:
        wrf_dates = '<span style="color:red">No recent data</span>'

    error_note = ''
    if 'error' in stats:
        error_note = f'<p style="color:red">DB query error: {stats["error"]}</p>'

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
    <h2>FloodWatch Daily Job Report</h2>
    <p><strong>Generated:</strong> {date_str}</p>
    {error_note}

    <h3>Multimodal Ensemble Forecasts</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;"><th>Data Date</th><th>Forecast Rows</th></tr>
        {mm_rows}
    </table>

    <h3>Google Flood API</h3>
    <p>Gauges: <strong>{gf.get('count', 'N/A'):,}</strong> | Last updated: {gf.get('last_updated', 'N/A')}</p>

    <h3>FloodProofs Deterministic</h3>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr style="background:#f0f0f0;"><th>Data Date</th><th>Features</th></tr>
        {fp_rows}
    </table>

    <h3>WRF Rainfall</h3>
    <p>Latest forecast dates: <strong>{wrf_dates}</strong></p>

    <hr>
    <p style="font-size:12px; color:#888;">
        This is an automated report from the FloodWatch Job Scheduler.
        Sent to: {', '.join(EMAIL_CONFIG['to_addrs'])}
    </p>
    </body>
    </html>
    """
    return html


def send_daily_report():
    """Query job stats and send daily email report."""
    if not EMAIL_CONFIG.get('enabled'):
        logger.info("Email notifications disabled")
        return

    smtp_user = EMAIL_CONFIG.get('smtp_user')
    smtp_password = EMAIL_CONFIG.get('smtp_password')
    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials not configured, skipping email report")
        return

    to_addrs = EMAIL_CONFIG.get('to_addrs', [])
    if not to_addrs:
        logger.warning("No recipients configured, skipping email report")
        return

    logger.info("Generating daily job report...")

    try:
        stats = _query_job_stats()
        html_body = _build_report_html(stats)

        today = datetime.now().strftime('%Y-%m-%d')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'FloodWatch Job Report - {today}'
        msg['From'] = EMAIL_CONFIG.get('from_addr', smtp_user)
        msg['To'] = ', '.join(to_addrs)

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(EMAIL_CONFIG['smtp_host'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(msg['From'], to_addrs, msg.as_string())

        logger.info(f"Daily report sent to {', '.join(to_addrs)}")

    except Exception as e:
        logger.error(f"Failed to send daily report: {e}")
