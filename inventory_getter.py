
import argparse
import re
import netmiko
import logging
import os
import sqlite3
import csv
from getpass import getpass
from datetime import datetime
from collections import namedtuple
from lxml import etree
from multiprocessing import Pool
from random import random
from time import sleep

logging.basicConfig(level=logging.DEBUG,
                    filename='inventory_getter.log',
                    format='%(asctime)s, %(levelname)s, %(message)s')

logger = logging.getLogger(__name__)


class DBHandlerError(BaseException):
    pass


class DBHandler:
    def __init__(self, dbname):
        self.dbname = dbname

    def create_table(self, table_name, fields):
        try:
            with sqlite3.connect(self.dbname) as con:
                task = (f'CREATE TABLE IF NOT EXISTS '
                        f'{table_name} ({fields}) ')
                con.execute(task)
        except sqlite3.Error as error:
            logger.error(error, exc_info=True)

    def execute(self, sql_request, parameters=None):
        try:
            with sqlite3.connect(self.dbname) as con:
                con.row_factory = sqlite3.Row
                cursor = con.cursor()
                if parameters is not None:
                    cursor.execute(sql_request, parameters)
                else:
                    cursor.execute(sql_request)
                return cursor.fetchall()
        except sqlite3.Error as error:
            logger.error(error, exc_info=True)

    def execute_many(self, sql_request, parameters_deck):
        try:
            with sqlite3.connect(self.dbname) as con:
                cursor = con.cursor()
                for parameters in parameters_deck:
                    cursor.execute(sql_request, parameters)
        except sqlite3.IntegrityError as error:
            logger.error(error, exc_info=True)
            raise DBHandlerError(error)
        except sqlite3.Error as error:
            logger.error(error, exc_info=True)

    def execute_many_scripts(self, querry_list, parameters_deck):
        try:
            with sqlite3.connect(self.dbname) as con:
                cursor = con.cursor()
                for parameters in parameters_deck:
                    for querry in querry_list:
                        cursor.execute(querry, parameters)
        except sqlite3.Error as error:
            logger.error(error, exc_info=True)

    def get_many(self, sql_list):
        list_of_responses = []
        try:
            with sqlite3.connect(self.dbname) as con:
                con.row_factory = sqlite3.Row
                cursor = con.cursor()
                for querry in sql_list:
                    cursor.execute(querry)
                    result = cursor.fetchall()
                    list_of_responses.append(tuple(result))
            return list_of_responses
        except sqlite3.Error as error:
            logger.error(error, exc_info=True)

    @staticmethod
    def dump_to_csv(data, file_name):
        fieldnames = data[0].keys()
        with open(file_name, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(dict(row))


class InventoryDBHandler(DBHandler):

    INVENTORY_DB_NAME = 'inventory'
    INVENTORY_DB_FIELDS = ('id INTEGER PRIMARY KEY, '
                           'hostname text, '
                           'ip text, '
                           'sw text, '
                           'name text, '
                           'version text, '
                           'part_number text, '
                           'serial_number text, '
                           'description text, '
                           'clei_code text, '
                           'model_number text')
    INSERT_INVENTORY_SQL = (f'INSERT INTO {INVENTORY_DB_NAME}'
                            f'(hostname, ip, sw, name, '
                            f'version, part_number, serial_number, '
                            f'description, clei_code, model_number) '
                            f'VALUES '
                            f'(:hostname, :ip, :sw, :name, '
                            f':version, :part_number, :serial_number, '
                            f':description, :clei_code, :model_number)')

    GET_ALL_SQL = f'SELECT * FROM {INVENTORY_DB_NAME}'

    def create_inventory_database(self):
        super().create_table(self.INVENTORY_DB_NAME,
                             self.INVENTORY_DB_FIELDS)

    def write_inventory(self, inventory_pack):
        super().execute_many(self.INSERT_INVENTORY_SQL, inventory_pack)

    def get_all_inventory(self):
        return super().execute(self.GET_ALL_SQL)

    def dump_inventory_to_csv(self, file_name):
        data = self.get_all_inventory()
        super().dump_to_csv(data, file_name)


class InventoryGetter:
    HW_INVENTORY_FIELDS = ('name', 'version', 'description',
                           'part-number', 'serial-number',
                           'clei-code', 'model-number')
    SW_FIELDS = ('hostname', 'ip', 'sw')
    TASK_FIELDS = ('name text,'
                   'gathered bool')
    MARTIAN_PATTERN = re.compile(r'[,.:;\"\'!?\s]')
    DUMMY_COMMAND = 'show version'
    SHOW_VER_COMMAND = 'show version | display xml | no-more'
    SHOW_CHAS_COMMAND = 'show chassis hardware | display xml | no-more'
    SW_VERSION_PATTERN = re.compile(r'\[(?P<vers>\d{2}.+)]')
    SW_VERSION_PATH_NORMAL = '//software-information/junos-version'
    SW_VERSION_PATH_EXCEPT = '//package-information[name[text()="junos"]]/comment'
    HOSTNAME_PATH = '//software-information/host-name'
    CLEAN_HOST_PATTERN = re.compile(r'[_\-]?[Rr][Ee][0-2]?\b$')
    LINUX_SW_COMMAND = 'ls {} | sort -hr | grep -E ".+_sw"'
    LINUX_HW_COMMAND = 'ls {} | sort -hr | grep -E ".+_hw$"'
    SW_FILE_PATTERN = re.compile('(?P<router>.+)_sw$', re.MULTILINE)
    HW_FILE_PATTERN = re.compile('(?P<router>.+)_hw$', re.MULTILINE)
    router_descriptor = namedtuple('router_object', ['name', 'hw', 'sw'])

    def __init__(self, db_object):
        self.db = db_object
        self.username = None
        self.password = None
        self.directory = None

    @staticmethod
    def read_list_from_file(text_file):
        with open(text_file, 'r') as file:
            return [r.strip() for r in file if r.strip()]

    @staticmethod
    def read_text_from_file(text_file):
        with open(text_file, 'r') as file:
            return file.read()

    def gather_inventory(self, router_list, username, password, workers=4):
        self.username = username
        self.password = password
        if len(router_list) >= workers:
            with Pool(workers) as p:
                list(p.map(self.ssh_worker, router_list))
        else:
            list(map(self.ssh_worker, router_list))

    def gather_from_routers_file(self, username, password, file, workers=4):
        router_list = self.read_list_from_file(file)
        self.gather_inventory(router_list, username, password, workers=workers)

    def gather_from_local_xmls(self, router, hw_file, sw_file):
        router_obj = self.router_descriptor(name=router,
                                            hw=hw_file,
                                            sw=sw_file)
        self.local_worker(router_obj)

    def gather_from_directory(self, directory, workers=4):
        self.directory = directory
        sw_files = os.popen(self.LINUX_SW_COMMAND.format(directory)).read()
        hw_files = os.popen(self.LINUX_HW_COMMAND.format(directory)).read()
        router_obj_list = self.get_router_object_list(sw_files, hw_files)
        if len(router_obj_list) >= workers:
            with Pool(workers) as p:
                list(p.map(self.local_worker, router_obj_list))
        else:
            list(map(self.local_worker, router_obj_list))

    def get_router_object_list(self, sw_files, hw_files):
        sw_routers_db = self.get_router_file_pairs(self.SW_FILE_PATTERN,
                                                   sw_files)
        if not sw_routers_db:
            logger.error('SW versions inventory files '
                         'not found in directory: {}'.format(self.directory))
            return
        sw_routers_set = set(sw_routers_db.keys())
        hw_routers_db = self.get_router_file_pairs(self.HW_FILE_PATTERN,
                                                   hw_files)
        if not hw_routers_db:
            logger.error('SW versions inventory files '
                         'not found in directory: {}'.format(self.directory))
            return
        hw_routers_set = set(hw_routers_db.keys())
        consistent_routers = sw_routers_set.intersection(hw_routers_set)
        all_routers = sw_routers_set.union(hw_routers_set)
        inconsistent_routers = all_routers.difference(consistent_routers)
        if inconsistent_routers:
            logger.notice('Not all files for '
                          'routers {}'.format(' '.join(inconsistent_routers)))
        router_list = []
        for router in consistent_routers:
            hw_file = '{}/{}'.format(self.directory, hw_routers_db[router])
            sw_file = '{}/{}'.format(self.directory, sw_routers_db[router])
            router_list.append(self.router_descriptor(name=router,
                                                      hw=hw_file,
                                                      sw=sw_file))
        return router_list

    @staticmethod
    def get_router_file_pairs(pattern, text_input):
        file_db = {}
        for element in pattern.finditer(text_input):
            router = element.group('router').strip()
            file_db[router] = element.group(0)
        return file_db

    def ssh_worker(self, router):
        try:
            raw_sw_text, raw_hw_text = self.data_getter(router)
            if not raw_sw_text or not raw_hw_text:
                return None
            inventory = self.parse_inventory(router, raw_sw_text, raw_hw_text)
            self.db.write_inventory(inventory)
            return True
        except BaseException as error:
            logger.error(error, exc_info=True)

    def local_worker(self, router_obj):
        try:
            raw_sw_text = self.read_text_from_file(router_obj.sw)
            raw_hw_text = self.read_text_from_file(router_obj.hw)
            inventory = self.parse_inventory(router_obj.name,
                                             raw_sw_text,
                                             raw_hw_text)
            self.db.write_inventory(inventory)
        except BaseException as error:
            logger.error(error, exc_info=True)

    def parse_inventory(self, router, raw_sw_text, raw_hw_text):
        sw_text = self.extract_rpc(raw_sw_text)
        hw_text = self.extract_rpc(raw_hw_text)
        if not sw_text or not sw_text:
            logger.debug('Inventory text not found for router {}'.format(router))
            return None
        sw_xml = etree.fromstring(sw_text)
        hw_xml = etree.fromstring(hw_text)
        inventory = self.rtabler(hw_xml)
        for position in inventory:
            position['ip'] = router
            position['sw'] = self.version_getter(sw_xml)
            position['hostname'] = self.hostname_getter(sw_xml)
        return inventory

    def data_getter(self, router):
        sleep(random() * 2)
        print('{}:{}_trying_to_connect_to_fetch_data'.format(self.ttime(), router))
        sw_text, hw_text = None, None
        try:
            with netmiko.ConnectHandler(ip=router,
                                        device_type='juniper_junos',
                                        username=self.username,
                                        password=self.password,
                                        global_delay_factor=4) as connect:
                print('{}:{}_conneceted'.format(self.ttime(), router))
                sleep(1)
                print('{}:{}_sending_test_command'.format(self.ttime(), router))
                test_command = connect.send_command(self.DUMMY_COMMAND)
                print('{}:{}_command_recieved'.format(self.ttime(), router))
                sleep(random())
                print('{}:{}_version_getting'.format(self.ttime(), router))
                sw_text = connect.send_command(self.SHOW_VER_COMMAND)
                print('{}:{}_version_gathered'.format(self.ttime(), router))
                sleep(random())
                print('{}:{}_hw_getting'.format(self.ttime(), router))
                hw_text = connect.send_command(self.SHOW_CHAS_COMMAND)
                print('{}:{}_hw_gathered'.format(self.ttime(), router))
                sleep(random())
            print('{}:{}_disconnected'.format(self.ttime(), router))
            return sw_text, hw_text
        except BaseException as error:
            print('{}:{} errror {}'.format(self.ttime(), router, error))
            logger.error(error, exc_info=True)
            return None, None

    @staticmethod
    def extract_rpc(inpstr):
        if inpstr.strip():
            start = inpstr.find('<rpc-reply')
            if start != -1:
                end = inpstr.find('</rpc-reply>')
                if end != -1:
                    end = end + len('</rpc-reply>')
                    return inpstr[start:end]

    def rtabler(self, element):
        table = []
        children = element.getchildren()
        if children:
            for child in children:
                table.extend(self.rtabler(child))
        row = self.extractor(element)
        if row:
            table.append(row)
        return table

    def normalize_text(self, raw_value):
        return self.MARTIAN_PATTERN.sub('_', raw_value)

    @staticmethod
    def remove_hyphens(raw_value):
        return re.sub(r'-+', '_', raw_value)

    def extractor(self, xmln):
        element = {}
        for field in self.HW_INVENTORY_FIELDS:
            raw_value = self.get_xpath(xmln, field, ignore_namespaces=True)
            field = self.remove_hyphens(field)
            element[field] = self.normalize_text(raw_value)
        element['name'] = element['name'].lower()
        return element if len(set(element.values())) > 1 else {}

    @staticmethod
    def ttime():
        return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    @staticmethod
    def get_xpath(xml, path, else_return='n_a', ignore_namespaces=False):
        if ignore_namespaces:
            path = './*[local-name() = "{}"]'.format(path)
        raw_res = xml.xpath(path)
        if raw_res:
            if raw_res[0].text:
                return raw_res[0].text.strip()
        return else_return

    def hostname_cleaner(self, raw_hostname):
        clean_hostname = raw_hostname.strip()
        clean_hostname = self.CLEAN_HOST_PATTERN.sub('', clean_hostname)
        return clean_hostname

    def version_getter(self, sw_xml):
        raw_sw = self.get_xpath(sw_xml,
                                self.SW_VERSION_PATH_NORMAL,
                                else_return='n_a')
        if raw_sw != 'n_a':
            return raw_sw.strip()
        raw_sw = self.get_xpath(sw_xml, self.SW_VERSION_PATH_EXCEPT)
        parsed_version = self.SW_VERSION_PATTERN.search(raw_sw)
        if parsed_version:
            clean_version = parsed_version.group('vers')
            if clean_version:
                return clean_version.strip()
        return 'n_a'

    def hostname_getter(self, sw_xml):
        raw_hostname = self.get_xpath(sw_xml, self.HOSTNAME_PATH).strip()
        clean_hostname = self.hostname_cleaner(raw_hostname)
        return clean_hostname

    def report_builder(self, file_name):
        print('{}:building_report'.format(self.ttime()))
        self.db.dump_inventory_to_csv(file_name)
        print('{}:report {} is ready'.format(self.ttime(), file_name))


def from_cli(inventory_object, args):
    inventory_object.gather_inventory(router_list=args.routers,
                                      username=args.user,
                                      password=getpass())


def from_routers_file(inventory_object, args):
    inventory_object.gather_from_routers_file(file=args.file,
                                              username=args.user,
                                              password=getpass())


def from_local_files(inventory_object, args):
    inventory_object.gather_from_local_xmls(router=args.router,
                                            hw_file=args.hw,
                                            sw_file=args.sw)


def from_directory(inventory_object, args):
    inventory_object.gather_from_directory(directory=args.directory)


def report(inventory_object, args):
    inventory_object.report_builder(file_name=args.file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers()
    parser_report = subparser.add_parser(
        'report',
        help='Build CSV report'
    )
    parser_report.add_argument(
        '--file',
        type=str,
        required=True,
        help='Set output file to dump csv'
    )
    parser_report.set_defaults(function=report)
    parser_routers = subparser.add_parser(
        'routers',
        help='Get inventory for set of routers'
    )
    parser_routers.add_argument(
        '--user',
        type=str,
        required=True,
        help='Set username for connection to routers'
    )
    parser_routers.add_argument(
        dest='routers',
        type=str,
        nargs='+',
        metavar='router..',
        help='specify routers to fetch inventory'
    )
    parser_routers.set_defaults(function=from_cli)
    parser_routers_file = subparser.add_parser(
        'routers_file',
        help='Get inventory for routers in file'
    )
    parser_routers_file.add_argument(
        dest='file',
        type=str,
        help='specify routers to fetch inventory'
    )
    parser_routers_file.add_argument(
        '--user',
        type=str,
        required=True,
        help='Set username for connection to router'
    )
    parser_routers_file.set_defaults(function=from_routers_file)
    parser_from_directory = subparser.add_parser(
        'directory',
        help='Get inventory from xml files stored in local directory'
    )
    parser_from_directory.add_argument(
        dest='directory',
        type=str,
        help='Set location of xml files'
    )
    parser_from_directory.set_defaults(function=from_directory)
    parser_local_files = subparser.add_parser(
        'local_files',
        help='Get inventory from single pair of xml files'
    )
    parser_local_files.add_argument(
        '--router',
        type=str,
        required=True,
        help='specify router name or ip'
    )
    parser_local_files.add_argument(
        '--sw',
        type=str,
        required=True,
        help='specify xml file with SW version'
    )
    parser_local_files.add_argument(
        '--hw',
        type=str,
        required=True,
        help='specify xml file with HW inventory'
    )
    parser_local_files.set_defaults(function=from_local_files)
    parser.add_argument(
        '--database',
        type=str,
        default='test_inv.db',
        help='specify database to store inventory'
    )
    arguments = parser.parse_args()
    inventory_database = InventoryDBHandler(arguments.database)
    inventory_database.create_inventory_database()
    inventory_handler = InventoryGetter(inventory_database)
    arguments.function(inventory_handler, arguments)
