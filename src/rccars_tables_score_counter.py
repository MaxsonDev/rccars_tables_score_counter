import os
import sys
import threading
import traceback
import keyboard
import tkinter as tk
from tkinter import ttk, Frame, Label, Text, Button, messagebox
from datetime import datetime
from race_table import get_rccars_pid, TableRaceResult


def get_icon_path():
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "icons", "icon.png")


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Недетские гонки. Таблицы результатов.")
        self.root.geometry("600x700")
        icon_path = get_icon_path()
        icon_image = tk.PhotoImage(file=icon_path)
        self.root.iconphoto(True, icon_image)

        # Игровые данные
        self.map_id_counter = 1
        self.table_result_dict = {}
        self.error_text = None

        # Запускаем глобальный слушатель F5
        self.start_global_f5_listener()

        # Создаем основной фрейм
        main_frame = Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ВЕРХНЯЯ ЧАСТЬ - ТАБЛИЦЫ (вертикальное расположение)
        tables_frame = Frame(main_frame)
        tables_frame.pack(fill=tk.BOTH, expand=True)

        # Таблица "Карта" (3 строки высотой)
        map_frame = Frame(tables_frame)
        map_frame.pack(fill=tk.X, pady=(0, 10))

        map_label = Label(map_frame, text="Карта", font=("Arial", 12, "bold"))
        map_label.pack(anchor=tk.W)

        self.map_table = ttk.Treeview(map_frame, columns=("id", "name", "time"), show="headings", height=3)
        self.map_table.heading("id", text="ID")
        self.map_table.heading("name", text="Имя карты")
        self.map_table.heading("time", text="Время создания")
        self.map_table.column("id", width=10)
        self.map_table.column("name", width=200)
        self.map_table.column("time", width=200)

        map_scrollbar = ttk.Scrollbar(map_frame, orient=tk.VERTICAL, command=self.map_table.yview)
        self.map_table.configure(yscrollcommand=map_scrollbar.set)

        self.map_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
        map_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Таблица "Результат" (6 строк высотой)
        result_frame = Frame(tables_frame)
        result_frame.pack(fill=tk.X, pady=(0, 10))

        result_label = Label(result_frame, text="Результат", font=("Arial", 12, "bold"))
        result_label.pack(anchor=tk.W)

        self.result_table = ttk.Treeview(result_frame, columns=("player", "score", "position"), show="headings", height=6)
        self.result_table.heading("player", text="Имя игрока")
        self.result_table.heading("score", text="Очков")
        self.result_table.heading("position", text="Место")
        self.result_table.column("player", width=160)
        self.result_table.column("score", width=20)
        self.result_table.column("position", width=20)

        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_table.yview)
        self.result_table.configure(yscrollcommand=result_scrollbar.set)

        self.result_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

         # СРЕДНЯЯ ЧАСТЬ - ОКНО ЛОГОВ
        logs_frame = Frame(main_frame)
        logs_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        logs_label = Label(logs_frame, text="Логи", font=("Arial", 12, "bold"))
        logs_label.pack(anchor=tk.W)

        # Текстовое поле для логов с прокруткой
        self.logs_text = Text(logs_frame, height=8, wrap=tk.WORD)
        logs_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.logs_text.yview)
        self.logs_text.configure(yscrollcommand=logs_scrollbar.set)

        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # НИЖНЯЯ ЧАСТЬ - КНОПКИ
        buttons_frame = Frame(main_frame)
        buttons_frame.pack(fill=tk.X)

        # Создаем кнопки
        self.refresh_button = Button(buttons_frame, text="Обновить", command=self.on_refresh_click, width=15)
        self.calculate_button = Button(buttons_frame, text="Посчитать результат", command=self.on_calculate_click,
                                       width=17)
        self.export_button = Button(buttons_frame, text="Удалить карту", command=self.on_delete_click, width=15)

        # Размещаем кнопки с отступами
        self.refresh_button.pack(side=tk.LEFT, padx=(70,0))
        self.calculate_button.pack(side=tk.LEFT, padx=(50,0))
        self.export_button.pack(side=tk.LEFT, padx=(50,0))

        # Привязываем обработчик выбора карты
        self.map_table.bind('<<TreeviewSelect>>', self.on_map_selected)

        # Инициализируем таблицу результатов как пустую
        self.clear_result_table()

        # Добавляем начальное сообщение в логи
        message = """Программа запущена!\nДля сохранения результатов заезда в таблицу нажми на клавишу F5.\nНажимать надо, когда все финишировали!\nЖелательно 1 раз!"""
        self.log_message(message)

        # На всякий проверим запущены ли Недетские гонки по pid
        pid = get_rccars_pid()
        if pid:
            text = 'Недетские гонки запущены!'
        else:
            text = 'Недетские гонки НЕ запущены! Для сохранения результатов нужно поиграть:)'
        self.log_message(text)

    def start_global_f5_listener(self):
        """Запускает глобальный слушатель для F5"""

        def listen_f5():
            keyboard.add_hotkey('f5', self.on_f5_pressed)
            keyboard.wait()  # Блокирующий вызов

        listener_thread = threading.Thread(target=listen_f5, daemon=True)
        listener_thread.start()

    def clear_result_table(self):
        """Очищаем таблицу результатов"""
        for item in self.result_table.get_children():
            self.result_table.delete(item)

    def clear_map_table(self):
        for item in self.map_table.get_children():
            self.map_table.delete(item)

    def log_message(self, message):
        """Добавляет сообщение в окно логов"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.logs_text.see(tk.END)  # Автопрокрутка к новому сообщению

    def update_tables(self):
        # Очищаем предыдущие данные во сех таблицах
        self.clear_map_table()
        self.clear_result_table()
        # Добавим карты из словаря
        for map_id, table in self.table_result_dict.items():
            self._add_map_in_table(map_id, table.map_name, table.ts)

    def calculate_results(self):
        tables = self.table_result_dict.values()
        if len(tables) == 0:
            return
        players_table = {}
        # считаем очки со всех заездов
        for table_data in tables:
            player_count = table_data.player_count
            for position, player_name in table_data.players_position.items():
                # проверим есть ли игрок в финальном списке. Если нет добавляем его в список со значением 0.
                is_player = players_table.get(player_name)
                if is_player is None:
                    players_table[player_name] = 0
                score = player_count - position
                players_table[player_name] += score
        finale_table = sorted(players_table.items(), key=lambda _score: _score[1], reverse=True)
        for position, data in enumerate(finale_table):
            position += 1
            self._add_player_in_table(data[0], data[1], position)
        # message = 'Для возвращения значений в таблицы нажми "Обновить".'
        # self.log_message(message)

    def _add_map_in_table(self, _id, map_name, ts):
        time = datetime.fromtimestamp(ts).strftime("%H:%M:%S %d.%m.%y")
        self.map_table.insert("", tk.END, values=(_id, map_name, time))

    def _add_players_in_table_standard(self, table):
        score = table.player_count
        for position, name in table.players_position.items():
            position += 1
            self._add_player_in_table(name, score, position)
            score -= 1

    def _add_player_in_table(self, name, score, position):
        self.result_table.insert("", tk.END, values=(name, score, position))

    # ОБРАБОТЧИКИ
    def on_map_selected(self, event):
        """Обработчик выбора карты в первой таблице"""
        selection = self.map_table.selection()
        if selection:
            selected_item = selection[0]
            item_values = self.map_table.item(selected_item, 'values')
            if item_values:
                map_id = int(item_values[0])
                self.clear_result_table()
                table = self.table_result_dict[map_id]
                self._add_players_in_table_standard(table)

    def on_refresh_click(self):
        """Обработчик кнопки 'Обновить'"""
        self.update_tables()

    def on_calculate_click(self):
        """Обработчик кнопки 'Посчитать результат'"""
        # Очищаем предыдущие данные во сех таблицах
        self.clear_map_table()
        self.clear_result_table()
        #
        self.calculate_results()

    def on_delete_click(self):
        """Обработчик кнопки 'Удалить'"""
        selection = self.map_table.selection()
        if bool(selection) is False:
            return
        selected_item = selection[0]
        item_values = self.map_table.item(selected_item, 'values')
        result = messagebox.askyesno(
            "Удаление карты",
            f"Вы уверены, что хотите удалить карту {item_values[1]} c ID {item_values[0]}?",
            icon='warning'
        )
        if result:
            # удалим карту
            map_id = int(item_values[0])
            del self.table_result_dict[map_id]
            self.log_message(f"Карта {item_values[1]} c ID {item_values[0]} удалена из списка.")
            # обновим список карт
            self.update_tables()

    def on_f5_pressed(self):
        try:
            table = TableRaceResult()
            table.get_race_result()
            if table.status == "OK":
                map_id = self.map_id_counter
                self.table_result_dict[map_id] = table
                self.map_id_counter += 1
                self._add_map_in_table(map_id, table.map_name, table.ts)
                self.clear_result_table()
                self._add_players_in_table_standard(table)
                message = f"Добавлен результат заезда на карте {table.map_name}! Участников: {table.player_count}."
            else:
                if table.status == "PID_IS_NONE":
                    message = "Игра не запущена! Запусти Недетские гонки!"
                elif table.status == "BAD_RACE_CODE":
                    message = "Записать можно только результат онлайн гонки. Или ты хочешь записать результат заезда с ботами?XD"
                elif table.status == "BAD_PLAYER_COUNT":
                    message = "Количество игроков в заезде равно 0! Скорее всего гонка не запущена."
                else:
                    message = "Что-то пошло не так.. Неизвестная ошибка."
            self.log_message(message)
        except:
            self.log_message(f"ОШИБКА В КОДЕ!!! ТЕКСТ НИЖЕ ОТПРАВИТЬ МАКСОНУ НА ИЗУЧЕНИЕ!\n\n{traceback.format_exc()}")


def main():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()