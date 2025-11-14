import re
import ctypes
import subprocess
import time
from ctypes import wintypes
from struct import unpack


ADDR_DAINS_POINT = 0x14B0730
ADDR_CAR_COUNT = 0x14B0988
ADDR_TYPE_RACE_CODE = 0x149A674
ADDR_MAP_NAME = 0x148F940
MAP_NAME_SIZE = 0x104
PLAYER_NAME_SIZE = 0x20


def read_bstring(bstring):
    zero_point = bstring.find(0)
    bstring = bstring[0:zero_point]
    return bstring.decode('cp1251')


def get_rccars_pid():
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    output = subprocess.check_output(['tasklist'], startupinfo=startupinfo, stderr=subprocess.STDOUT, text=True, encoding="cp866")
    rccars_line = re.search(r'RCCars\.exe.+', output)
    if rccars_line is None:
        return None
    all_integers = re.findall(r'\d+', rccars_line[0])
    return int(all_integers[0])


class TableRaceResult:
    def __init__(self):
        kernel32 = ctypes.windll.kernel32
        self._OpenProcess = kernel32.OpenProcess
        self._ReadProcessMemory = kernel32.ReadProcessMemory
        self._CloseHandle = kernel32.CloseHandle
        self.PROCESS_VM_READ = 0x0010
        self.pid = None
        self.status = None
        self.ts = None
        self.process_handle = None

        self.map_name = None
        self.player_count = None
        self.players_position = {}

    def get_race_result(self):
        pid = get_rccars_pid()
        if pid is None:
            self.status = "PID_IS_NONE"
            return
        self.pid = pid
        # Race Code
        race_code = self._read_process_memory(ADDR_TYPE_RACE_CODE, 4)
        race_code = unpack("I", race_code)[0]
        # race_code 7 и 8 это онлайн заезды.
        # 1 - обычная гонка, но не думаю что кому-то надо считать заезды с ботами. нужно только для тестов на таблице ботов
        if race_code not in (7, 8):
            self.status = "BAD_RACE_CODE"
            return
        # Players Count
        players_count = self._read_process_memory(ADDR_CAR_COUNT, 4)
        players_count = unpack("I", players_count)[0]
        if players_count == 0:
            self.status = "BAD_PLAYER_COUNT"
            return
        for i in range(players_count):
            player_name = self._get_player_name(i)
            self.players_position[i] = player_name
        self.player_count = players_count
        # Map Name
        self._get_map_name()
        self.ts = time.time()
        self.status = "OK"

    def _get_map_name(self):
        map_dict = {
            'beach_1': 'Пляж',
            'beach_2': 'Кемпинг',
            'beach_3': 'Форт',
            'beach_4': 'Война',
            'country_1': 'Ранчо',
            'country_2': 'Шахта',
            'country_3': 'Деревня',
            'country_4': 'СС-30',
            'urban_1': 'Объект X',
            'urban_2': 'База ПВО'
        }
        map_name = self._read_process_memory(ADDR_MAP_NAME, MAP_NAME_SIZE)
        map_name = read_bstring(map_name)
        self.map_name = map_dict[map_name.lower()]

    def _get_player_name(self, step):
        # DAINS - это объекты в Rc Cars, которые хранят данные о машинках во время заезда.
        # добавляем к указателю ADDR_DAINS_POINT 64h умноженное на позицию машинки в таблице, чтобы получить адрес на нужный DAINS
        DAINS_addr_offset = ADDR_DAINS_POINT + step * 0x64
        DAINS_address = self._read_process_memory(DAINS_addr_offset, 4)
        DAINS_address = unpack("I", DAINS_address)[0]
        # имя игрока или бота хранится на DAINS + 14h
        player_name_address = DAINS_address + 0x14
        player_name = self._read_process_memory(player_name_address, PLAYER_NAME_SIZE)
        return read_bstring(player_name)

    def _open_process(self):
        self.process_handle = self._OpenProcess(self.PROCESS_VM_READ, False, self.pid)
        if self.process_handle:
            return self.process_handle
        return None

    def _read_process_memory(self, address, size):
        if self.process_handle is None:
            self._open_process()
        buffer = ctypes.create_string_buffer(size)
        bytes_read = wintypes.SIZE()
        success = self._ReadProcessMemory(
            self.process_handle,
            address,
            buffer,
            size,
            ctypes.byref(bytes_read)
        )
        if success:
            result = buffer.raw
            return result
        return None

    def _close_handle(self):
        if self.process_handle:
            self._CloseHandle(self.process_handle)
            self.process_handle = None

    def __del__(self):
        self._close_handle()
