import subprocess
from os import environ
from datetime import datetime
import json
from typing import Dict


def seed_dekadal_datasets(
    tileset: str,
    start_year: int | None = 2020,
    final_year: int | None = 2023,
    final_month: int = 12,
    final_dekad: int = 21,
    dekads: list[int] = [1, 11, 21],
):
    cmd = """
    mapcache_seed --config /mapcache/mapcache.xml --tileset {tileset} 
    --ogr-datasource "postgresql://{DB_MAP_USER}:{DB_MAP_USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 
    --ogr-sql "SELECT ST_Transform(ST_Union(geom),900913) 
    FROM thematic.gadm4_admin_level0_boundaries" 
    --zoom 4,8  --nthreads 8 -D "SELECTED_TENDAYS={dekad}" -D "SELECTED_DMONTH={month}" 
    -D "SELECTED_YEAR={year}" --log-failed /mapcache/failed-{tileset}-tiles.log --verbose
    """  # noqa: E501
    start_year = int(start_year)
    final_year = int(final_year)
    final_month = int(final_month)
    final_dekad = int(final_dekad)
    start_time = datetime.now()
    for year in range(start_year, final_year + 1):
        month_range = range(1, 13) if year != final_year else range(1, final_month + 1)
        for month in month_range:
            dekads_list = (
                dekads
                if year != final_year and month != final_month
                else dekads[: dekads.index(final_dekad) + 1]
            )
            for dekad in dekads_list:
                print(
                    f"executing mapcache seeder program for {tileset} with arguments"
                    + f" year={year} month={month} dekad={dekad}"
                )
                try:
                    process = subprocess.run(
                        cmd.format(
                            tileset=tileset,
                            year=year,
                            month=str(month).rjust(2, "0"),
                            dekad=str(dekad).rjust(2, "0"),
                            DB_MAP_USER=environ.get("DB_MAP_USER", "postgres"),
                            DB_MAP_USER_PASSWORD=environ.get(
                                "DB_MAP_USER_PASSWORD", "<top-secret>"
                            ),
                            DB_HOST=environ.get("DB_HOST", "172.17.0.1"),
                            DB_PORT=environ.get("DB_PORT", "5432"),
                            DB_NAME=environ.get("DB_NAME", "mukau_mapserver"),
                        ).replace("\n    ", ""),
                        capture_output=True,
                        encoding="utf-8",
                        shell=True,
                        check=True,
                    )
                except Exception as err:
                    print(f"{tileset} seeder program failed with error {err}")
                else:
                    print(
                        f"{tileset} seeder program completed successfully for "
                        + f"year={year} month={month} dekad={dekad}"
                    )

    final_time = datetime.now()
    print(f"start_time = {start_time}, final_time = {final_time}")
    print(
        f"{tileset} tile generation for {start_year}-01 to {final_year}-{final_month} "
        + f"took a total of {final_time-start_time}"
    )


def seed_monthly_datasets(
    tileset: str,
    start_year: int | None = 2020,
    final_year: int | None = 2023,
    final_month: str = "dec",
):
    cmd = """
    mapcache_seed --config /mapcache/mapcache --tileset {tileset} 
    --ogr-datasource "postgresql://{DB_MAP_USER}:{DB_MAP_USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 
    --ogr-sql "SELECT ST_Transform(ST_Union(geom),900913) 
    FROM thematic.gadm4_admin_level0_boundaries" 
    --zoom 4,8  --nthreads 8 -D "SELECTED_MONTH={month}" -D "SELECTED_YEAR={year}" 
    --log-failed /mapcache/failed-{tileset}-tiles.log --verbose
    """  # noqa: E501
    start_year = int(start_year)
    final_year = int(final_year)
    start_time = datetime.now()
    months = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    for year in range(start_year, final_year + 1):
        month_range = (
            months if year != final_year else months[: months.index(final_month) + 1]
        )
        for month in month_range:
            print(
                f"executing mapcache seeder program for {tileset} with arguments"
                + f" year={year} month={month}"
            )
            try:
                process = subprocess.run(
                    cmd.format(
                        tileset=tileset,
                        year=year,
                        month=month,
                        DB_MAP_USER=environ.get("DB_MAP_USER", "postgres"),
                        DB_MAP_USER_PASSWORD=environ.get(
                            "DB_MAP_USER_PASSWORD", "<top-secret>"
                        ),
                        DB_HOST=environ.get("DB_HOST", "172.17.0.1"),
                        DB_PORT=environ.get("DB_PORT", "5432"),
                        DB_NAME=environ.get("DB_NAME", "mukau_mapserver"),
                    ).replace("\n    ", ""),
                    capture_output=True,
                    encoding="utf-8",
                    shell=True,
                    check=True,
                )
            except Exception as err:
                print(f"{tileset} seeder program failed with error {err}")
            else:
                print(
                    f"{tileset} seeder program completed successfully for "
                    + f"year={year} month={month}"
                )

    final_time = datetime.now()
    print(f"start_time = {start_time}, final_time = {final_time}")
    print(
        f"{tileset} tile generation for {start_year}-01 to {final_year}-{final_month} "
        + f"tooks a total of {final_time-start_time}"
    )


def seed_seasonal_datasets(
    tileset: str,
    start_year: int | None = 2020,
    final_year: int | None = 2023,
    final_month: str = "oct_dec",
):
    cmd = """
    mapcache_seed --config /mapcache/mapcache --tileset {tileset} 
    --ogr-datasource "postgresql://{DB_MAP_USER}:{DB_MAP_USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 
    --ogr-sql "SELECT ST_Transform(ST_Union(geom),900913) 
    FROM thematic.gadm4_admin_level0_boundaries" 
    --zoom 4,8  --nthreads 8 -D "SELECTED_SEASON={season}" -D "SELECTED_YEAR={year}" 
    --log-failed /mapcache/failed-{tileset}-tiles.log --verbose
    """  # noqa: E501
    start_year = int(start_year)
    final_year = int(final_year)
    start_time = datetime.now()
    seasons = [
        "jan_mar",
        "mar_may",
        "jun_sep",
        "oct_dec",
    ]
    for year in range(start_year, final_year + 1):
        season_range = (
            seasons if year != final_year else seasons[: seasons.index(final_month) + 1]
        )
        for season in season_range:
            print(
                f"executing mapcache seeder program for {tileset} with arguments"
                + f" year={year} season={season}"
            )
            try:
                process = subprocess.run(
                    cmd.format(
                        tileset=tileset,
                        year=year,
                        season=season,
                        DB_MAP_USER=environ.get("DB_MAP_USER", "postgres"),
                        DB_MAP_USER_PASSWORD=environ.get(
                            "DB_MAP_USER_PASSWORD", "<top-secret>"
                        ),
                        DB_HOST=environ.get("DB_HOST", "172.17.0.1"),
                        DB_PORT=environ.get("DB_PORT", "5432"),
                        DB_NAME=environ.get("DB_NAME", "mukau_mapserver"),
                    ).replace("\n    ", ""),
                    capture_output=True,
                    encoding="utf-8",
                    shell=True,
                    check=True,
                )
            except Exception as err:
                print(f"{tileset} seeder program failed with error {err}")
            else:
                print(
                    f"{tileset} seeder program completed successfully for "
                    + f"year={year} season={season}"
                )

    final_time = datetime.now()
    print(f"start_time = {start_time}, final_time = {final_time}")
    print(
        f"{tileset} tile generation for {start_year}-01 to {final_year}-{final_month} "
        + f"tooks a total of {final_time-start_time}"
    )


def seed_spi_datasets(
    tileset: str,
    timescale: str,
    start_year: int | None = 2020,
    final_year: int | None = 2023,
    final_month: str = "dec",
):
    cmd = """
    mapcache_seed --config /mapcache/mapcache --tileset {tileset} 
    --ogr-datasource "postgresql://{DB_MAP_USER}:{DB_MAP_USER_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 
    --ogr-sql "SELECT ST_Transform(ST_Union(geom),900913) 
    FROM thematic.gadm4_admin_level0_boundaries" 
    --zoom 4,8  --nthreads 8 -D "SELECTED_TIMESCALE={timescale}" -D "SELECTED_MONTH={month}" -D "SELECTED_YEAR={year}" 
    --log-failed /mapcache/failed-{tileset}-tiles.log --verbose
    """  # noqa: E501
    start_year = int(start_year)
    final_year = int(final_year)
    start_time = datetime.now()
    months = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    for year in range(start_year, final_year + 1):
        month_range = (
            months if year != final_year else months[: months.index(final_month) + 1]
        )
        for month in month_range:
            print(
                f"executing mapcache seeder program for {tileset} with arguments"
                + f" year={year} month={month} timescale={timescale}"
            )
            try:
                process = subprocess.run(
                    cmd.format(
                        tileset=tileset,
                        year=year,
                        month=month,
                        timescale=timescale,
                        DB_MAP_USER=environ.get("DB_MAP_USER", "postgres"),
                        DB_MAP_USER_PASSWORD=environ.get(
                            "DB_MAP_USER_PASSWORD", "<top-secret>"
                        ),
                        DB_HOST=environ.get("DB_HOST", "172.17.0.1"),
                        DB_PORT=environ.get("DB_PORT", "5432"),
                        DB_NAME=environ.get("DB_NAME", "mukau_mapserver"),
                    ).replace("\n    ", ""),
                    capture_output=True,
                    encoding="utf-8",
                    shell=True,
                    check=True,
                )
            except Exception as err:
                print(f"{tileset} seeder program failed with error {err}")
            else:
                print(
                    f"{tileset} seeder program completed successfully for "
                    + f"year={year} month={month} timescale={timescale}"
                )

    final_time = datetime.now()
    print(f"start_time = {start_time}, final_time = {final_time}")
    print(
        f"{tileset} tile generation for {start_year}-01 to {final_year}-{final_month} "
        + f"tooks a total of {final_time-start_time}"
    )


if __name__ == "__main__":
    with open("./tilesets.json") as tc:
        config: list[Dict[str, str]] = json.loads(tc.read())
    for item in config:
        if item["period"] == "dekadal":
            seed_dekadal_datasets(
                **{key: value for key, value in item.items() if key != "period"}
            )  # noqa: E501
        elif item["period"] == "monthly":
            seed_monthly_datasets(
                **{key: value for key, value in item.items() if key != "period"}
            )  # noqa: E501
        elif item["period"] == "seasonal":
            seed_seasonal_datasets(
                **{key: value for key, value in item.items() if key != "period"}
            )  # noqa: E501
        elif item["period"] == "timescale":
            for timescale in ["01", "03", "06", "09", "12", "24", "48"]:
                seed_spi_datasets(
                    timescale=timescale,
                    **{key: value for key, value in item.items() if key != "period"},
                )  # noqa: E501
