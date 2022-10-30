## Inventory Getter
Simple python solution to get hardware and software inventory for Juniper Devices and store it in SQLlite Database.
Uses Netmiko and LXML underlying libraries. Provides simple CLI interface.

## Install
Script is cautiosly delivered as a single file to preserve it's consistency during server to server copying in a very dynaimc network operations environment.  
However it could installed with a very standard approach.
```
git clone 
pip3 install -r requirements.txt
```

## How to Use
The inventory getter provides several scenarios of work
- [Get inventory from remote devices](#get-inventory-from-remote-devices)
- [Get inventory from local directory](#get-inventory-from-a-local-directory)
- [Get inventory from local files](#get-inventory-from-local-files)
- [Export SQL database to csv](#export-sql-database-to-csv)

[Resulting SQL database](#resulting-sql-database)

Script provides help at each step of execution, specify database file to dump inventory.  
The test_inv.db file will be created by default, if --database argument is not specified.

```
python3 inventory_getter.py --help
usage: inventory_getter.py [-h] [--database DATABASE] {report,routers,routers_file,directory,local_files} ...

positional arguments:
  {report,routers,routers_file,directory,local_files}
    report              Build CSV report
    routers             Get inventory for set of routers
    routers_file        Get inventory for routers in file
    directory           Get inventory from xml files stored in local directory
    local_files         Get inventory from single pair of xml files

optional arguments:
  -h, --help            show this help message and exit
  --database DATABASE   specify database to store inventory
```

### Get inventory from remote devices
Script requires username to get login to devices. Password is specified via cli once the script starts.
Optionally remote TCP port could be specified, standard 22 used by default.

Remote devices could be specified as set of hostname/ip-addresses or file contained hostname/ip-addresses.

Script run with routers specified as set of hostname/ip-addresses:
```
python3 inventory_getter.py routers 10.85.150.69 10.85.150.71  --user root    
Password: 
```
Script run with routers file example:
```
python3 inventory_getter.py new_test_inv.db routers_file routers.txt --user root 
Password:
```
If the routers file is used, the format of router file must be trivial and contain one hostname\ip-address per line.

Example:
```
10.85.150.69
10.85.150.71
```
#### Sample start
Script throws the following notifications to stdout during execution reporting its' progress.
```
2022_10_26_21_17_13:10.85.150.69_trying_to_connect_to_fetch_data
2022_10_26_21_17_22:10.85.150.69_conneceted
2022_10_26_21_17_23:10.85.150.69_sending_test_command
2022_10_26_21_17_26:10.85.150.69_command_recieved
2022_10_26_21_17_27:10.85.150.69_version_getting
2022_10_26_21_17_30:10.85.150.69_version_gathered
2022_10_26_21_17_30:10.85.150.69_hw_getting
2022_10_26_21_17_33:10.85.150.69_hw_gathered
2022_10_26_21_17_34:10.85.150.69_disconnected
2022_10_26_21_17_34:10.85.150.71_trying_to_connect_to_fetch_data
2022_10_26_21_17_44:10.85.150.71_conneceted
2022_10_26_21_17_45:10.85.150.71_sending_test_command
2022_10_26_21_17_48:10.85.150.71_command_recieved
2022_10_26_21_17_49:10.85.150.71_version_getting
2022_10_26_21_17_52:10.85.150.71_version_gathered
2022_10_26_21_17_52:10.85.150.71_hw_getting
2022_10_26_21_17_55:10.85.150.71_hw_gathered
2022_10_26_21_17_56:10.85.150.71_disconnected
```
### Get inventory from a local directory
If remote gathering of inventory information is not possible, local files with software and hardware inventoru could be stored in local directory and parsed into SQL database.
- Software inventory it's an output of command `show version | display xml` saved in filename with postfix _sw
- Hardware inventory it's an output of command `show chassis hardware | display xml` saved in filename with postfix _hw
```
ls local_dir 
qfx10k_hw	qfx10k_sw	qfx5k_hw	qfx5k_sw
```
Script execution example to get inventory from a local directory
```
python3 inventory_getter.py --database test_local.db directory local_dir 
```
In case of local directory execution file prefix (before _sw/_hw postfix) is copied into inventory Field IP. Hostname is exacted from _sw inventory file.

### Get inventory from local files
Script allows specify explicit sw and hw files to parse a single router inventory information.
Argument `--router` populate IP field in inventory database
Script execution example to get inventory from local files
```
python3 inventory_getter.py --database single.db local_files --sw local_dir/qfx5k_sw --hw local_dir/qfx5k_hw --router test_local
```
### Export SQL database to csv
Script execution example dump sql database into csv.  Argument `--file` specifies destination file.
```
python3 inventory_getter.py  --database test_inv.db report --file test_report_out.csv
2022_10_30_16_30_21:building_report
2022_10_30_16_30_21:report test_report_out.csv is ready
```

### Resulting SQL database
id|hostname|ip|sw|name|version|part_number|serial_number|description|clei_code|model_number
--- | --- | --- | --- | --- | --- | --- | --- |--- | --- | --- 
1|qfx-spine|10.85.150.69|20.2R3-S3.6|pseudo_cb_0|n_a|n_a|XXX|n_a|n_a|n_a
2|qfx-spine|10.85.150.69|20.2R3-S3.6|routing_engine_0|n_a|BUILTIN|XXX|RE-QFX10002-36Q|CMMTM00ARA|QFX10002-36Q-CHAS
3|qfx-spine|10.85.150.69|20.2R3-S3.6|cpu|n_a|BUILTIN|XXX|FPC_CPU|n_a|n_a
4|qfx-spine|10.85.150.69|20.2R3-S3.6|xcvr_0|REV_01|740-067442|XXX|QSFP+-40G-SR4|n_a|n_a
5|qfx-spine|10.85.150.69|20.2R3-S3.6|xcvr_1|REV_01|740-067442|XXX|QSFP+-40G-SR4|n_a|n_a
6|qfx-spine|10.85.150.69|20.2R3-S3.6|xcvr_2|REV_01|740-046565|XXX|QSFP+-40G-SR4|n_a|n_a
7|qfx-spine|10.85.150.69|20.2R3-S3.6|xcvr_10|REV_01|740-046565|XXX|QSFP+-40G-SR4|n_a|n_a
8|qfx-spine|10.85.150.69|20.2R3-S3.6|pic_0|n_a|BUILTIN|XXX|36X40G|CMMTM00ARA|QFX10002-36Q-CHAS
9|qfx-spine|10.85.150.69|20.2R3-S3.6|mezz|REV_02|711-059316|XXX|QFX10002_36X40G_Mezz|n_a|n_a
10|qfx-spine|10.85.150.69|20.2R3-S3.6|fpc_0|REV_26|750-059497|XXX|QFX10002-36Q|CMMTM00ARA|QFX10002-36Q-CHAS
11|qfx-spine|10.85.150.69|20.2R3-S3.6|power_supply_0|REV_03|740-054405|XXX|AC_AFO_1600W_PSU|CMUPADHBAA|JPSU-1600W-AC-AFO
12|qfx-spine|10.85.150.69|20.2R3-S3.6|power_supply_1|REV_03|740-054405|XXX|AC_AFO_1600W_PSU|CMUPADHBAA|JPSU-1600W-AC-AFO
13|qfx-spine|10.85.150.69|20.2R3-S3.6|fan_tray_0|n_a|n_a|XXX|QFX10002_Fan_Tray_0__Front_to_Back_Airflow_-_AFO|n_a|QFX10002__Assy_Sub_80mm_Fan_Tray_AFO-AFO
14|qfx-spine|10.85.150.69|20.2R3-S3.6|fan_tray_1|n_a|n_a|XXX|QFX10002_Fan_Tray_1__Front_to_Back_Airflow_-_AFO|n_a|QFX10002__Assy_Sub_80mm_Fan_Tray_AFO-AFO
15|qfx-spine|10.85.150.69|20.2R3-S3.6|fan_tray_2|n_a|n_a|XXX|QFX10002_Fan_Tray_2__Front_to_Back_Airflow_-_AFO|n_a|QFX10002__Assy_Sub_80mm_Fan_Tray_AFO-AFO
16|qfx-spine|10.85.150.69|20.2R3-S3.6|chassis|n_a|n_a|XXX|QFX10002-36Q|n_a|n_a
17|qfx-tor|10.85.150.71|20.2R3.9|pseudo_cb_0|n_a|n_a|XXX|n_a|n_a|n_a
18|qfx-tor|10.85.150.71|20.2R3.9|routing_engine_0|n_a|BUILTIN|XXX|RE-QFX5200-32C-32Q|CMMUC00ARA|QFX5200-32C-AFO
19|qfx-tor|10.85.150.71|20.2R3.9|cpu|n_a|BUILTIN|XXX|FPC_CPU|n_a|n_a
20|qfx-tor|10.85.150.71|20.2R3.9|xcvr_0|REV_01|740-067442|XXX|QSFP+-40G-SR4|n_a|n_a
21|qfx-tor|10.85.150.71|20.2R3.9|xcvr_1|REV_01|740-067442|XXX|QSFP+-40G-SR4|n_a|n_a
22|qfx-tor|10.85.150.71|20.2R3.9|xcvr_2|REV_01|740-032986|XXX|QSFP+-40G-SR4|n_a|n_a
23|qfx-tor|10.85.150.71|20.2R3.9|xcvr_10|REV_01|740-067442|XXX|QSFP+-40G-SR4|n_a|n_a
24|qfx-tor|10.85.150.71|20.2R3.9|pic_0|n_a|BUILTIN|XXX|32X40G/32X100G-QSFP|CMMUC00ARA|QFX5200-32C-AFO
25|qfx-tor|10.85.150.71|20.2R3.9|fpc_0|n_a|650-059719|XXX|QFX5200-32C-32Q|CMMUC00ARA|QFX5200-32C-AFO
26|qfx-tor|10.85.150.71|20.2R3.9|power_supply_0|REV_03|740-053352|XXX|JPSU-850W-AC-AFO|CMUPACSBAC|JPSU-850W-AC-AFO
27|qfx-tor|10.85.150.71|20.2R3.9|fan_tray_0|n_a|n_a|XXX|QFX5200_Fan_Tray_0__Front_to_Back_Airflow_-_AFO|n_a|QFX5200-FAN-AFO
28|qfx-tor|10.85.150.71|20.2R3.9|fan_tray_1|n_a|n_a|XXX|QFX5200_Fan_Tray_1__Front_to_Back_Airflow_-_AFO|n_a|QFX5200-FAN-AFO
29|qfx-tor|10.85.150.71|20.2R3.9|fan_tray_2|n_a|n_a|XXX|QFX5200_Fan_Tray_2__Front_to_Back_Airflow_-_AFO|n_a|QFX5200-FAN-AFO
30|qfx-tor|10.85.150.71|20.2R3.9|fan_tray_3|n_a|n_a|XXX|QFX5200_Fan_Tray_3__Front_to_Back_Airflow_-_AFO|n_a|QFX5200-FAN-AFO
31|qfx-tor|10.85.150.71|20.2R3.9|fan_tray_4|n_a|n_a|XXX|QFX5200_Fan_Tray_4__Front_to_Back_Airflow_-_AFO|n_a|QFX5200-FAN-AFO
32|qfx-tor|10.85.150.71|20.2R3.9|chassis|n_a|n_a|XXX|QFX5200-32C-32Q|n_a|n_a