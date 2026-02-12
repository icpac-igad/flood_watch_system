"""
Populate whca_selected flag on gha.multimodal_control_points for the 381 curated
WHCA control points (from the WHCA project seed data).

These 381 points are the curated subset across 5 WHCA countries:
  - South Sudan: 222
  - Uganda: 84
  - Sudan: 57
  - Ethiopia: 17
  - Rwanda: 1

When the WHCA filter is active in the mapviewer, pg_tileserv calls
gha.multimodal_points_clustered_whca() which filters by whca_selected = true.
"""

from django.db import migrations


# 381 curated WHCA point_ids extracted from the WHCA project seed data
# (whca/geomanager-web/docker/cms/seed/sql/002_seed_whca_selected_points.sql)
WHCA_POINT_IDS = [
    112, 114, 173, 174, 194, 199, 219, 221, 222, 229, 236, 242, 243, 244,
    246, 255, 263, 284, 294, 301, 314, 326, 328, 336, 346, 364, 403, 404,
    405, 406, 417, 427, 431, 455, 457, 469, 471, 478, 513, 516, 518, 523,
    582, 591, 600, 611, 618, 619, 620, 622, 628, 629, 653, 657, 658, 667,
    669, 681, 692, 725, 728, 729, 748, 751, 752, 763, 784, 795, 811, 813,
    826, 851, 863, 874, 877, 895, 926, 932, 945, 949, 958, 962, 968, 974,
    978, 1000, 1002, 1006, 1012, 1014, 1015, 1019, 1022, 1027, 1033, 1034,
    1036, 1039, 1040, 1042, 1044, 1045, 1047, 1048, 1055, 1059, 1063, 1064,
    1066, 1067, 1068, 1072, 1073, 1077, 1078, 1079, 1080, 1084, 1087, 1088,
    1090, 1092, 1093, 1095, 1096, 1097, 1098, 1102, 1103, 1105, 1106, 1110,
    1111, 1113, 1114, 1115, 1116, 1117, 1125, 1126, 1129, 1130, 1133, 1134,
    1135, 1137, 1139, 1140, 1141, 1142, 1143, 1144, 1145, 1147, 1149, 1151,
    1153, 1155, 1157, 1158, 1160, 1161, 1162, 1163, 1165, 1166, 1167, 1169,
    1171, 1172, 1173, 1175, 1176, 1177, 1178, 1179, 1180, 1182, 1184, 1185,
    1186, 1187, 1188, 1190, 1191, 1192, 1197, 1199, 1203, 1204, 1205, 1206,
    1207, 1208, 1210, 1211, 1212, 1215, 1217, 1218, 1219, 1220, 1222, 1224,
    1225, 1226, 1227, 1228, 1230, 1231, 1233, 1235, 1236, 1238, 1241, 1242,
    1243, 1244, 1245, 1246, 1247, 1248, 1249, 1250, 1252, 1257, 1258, 1259,
    1260, 1261, 1265, 1269, 1270, 1271, 1273, 1274, 1275, 1278, 1279, 1280,
    1282, 1283, 1285, 1286, 1288, 1293, 1294, 1296, 1297, 1298, 1299, 1302,
    1305, 1306, 1307, 1308, 1311, 1313, 1315, 1316, 1322, 1329, 1330, 1331,
    1334, 1335, 1336, 1338, 1340, 1341, 1342, 1345, 1347, 1349, 1351, 1352,
    1354, 1357, 1358, 1359, 1360, 1365, 1368, 1369, 1370, 1371, 1372, 1374,
    1375, 1376, 1377, 1380, 1382, 1383, 1384, 1385, 1389, 1390, 1391, 1392,
    1393, 1394, 1395, 1397, 1398, 1399, 1400, 1401, 1402, 1403, 1404, 1405,
    1406, 1407, 1408, 1409, 1410, 1411, 1412, 1413, 1414, 1415, 1416, 1417,
    1418, 1419, 1420, 1421, 1422, 1423, 1424, 1425, 1426, 1427, 1428, 1429,
    1431, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1439, 1440, 1441, 1442,
    1443, 1444, 1445, 1446, 1447, 1448, 1449, 1456, 1457, 1458, 1459, 1462,
    1464, 1465, 1466, 1472, 1475, 1478, 1481, 1482, 1484, 1488, 1490, 1496,
    1501, 1502, 1506, 1514, 1531, 1537, 1539, 1561, 1574,
]


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0033_update_gha_multimodal_cluster_grid_size"),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"""
-- Reset all whca_selected to false first
UPDATE gha.multimodal_control_points SET whca_selected = false;

-- Set whca_selected = true for the 381 curated WHCA points
UPDATE gha.multimodal_control_points
SET whca_selected = true
WHERE point_id IN ({','.join(str(pid) for pid in WHCA_POINT_IDS)});
""",
            reverse_sql="""
-- Reverse: reset all whca_selected to false
UPDATE gha.multimodal_control_points SET whca_selected = false;
""",
        ),
    ]
