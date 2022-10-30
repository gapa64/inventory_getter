##Inventory Getter
Simple python solution to get hardware and software inventory for Juniper Devices and store it in SQLlite Database.
Uses Netmiko and LXML underlying libraries. Provide simple CLI interface.

###Install
```
git clone 
pip3 install -r requirements.txt
```

### How to Use
The inventory getter provides several scenarios 
- [Get inventory from remote devices](#get-inventory-from-remote-devices)
- [Get inventory from local directory](#get-inventory-from-local-directory)
- [Get inventory for particular files](#get-inventory-for-single)
- [Export SQL Database to CVS](#export-sql-database-to-csv)

There are several examples of API calls

### Get inventory from remote routers
Script requires several attributes to login, 
- username
- routers
```
inventory_getter % python3 inventory_getter.py --help
usage: inventory_getter.py [-h] [--database DATABASE] {routers,routers_file,directory,local_files} ...

positional arguments:
  {routers,routers_file,directory,local_files}
    routers             Get inventory for set of routers
    routers_file        Get inventory for routers in file
    directory           Get inventory from xml files stored in local directory
    local_files         Get inventory from single pair of xml files

optional arguments:
  -h, --help            show this help message and exit
  --database DATABASE   specify database to store inventory
```

If the routers file is used, the format of router file must be trivial and contain one hostname\ip-address per line
example:

```
10.85.150.69
10.85.150.71
```
#### Sample start
```
python3 inventory_getter.py routers 10.85.150.69 10.85.150.71  --user root    
Password: 
```

Script throws the following notificcations to stdoud during execution reporting its' progress.

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

```
python3 inventory_getter.py  --database test_inv.db report --file test_report_out.csv
2022_10_30_16_30_21:building_report
2022_10_30_16_30_21:report test_report_out.csv is ready
```
