/home/dukhanin/agile_new/analysis/data_for_spb_hakaton_entities/data_for_spb_hakaton_entities1-Table 1.csv
<class 'pandas.core.frame.DataFrame'>
MultiIndex: 2486 entries, ('entity_id', 'area', 'type', 'status', 'state', 'priority', 'ticket_number', 'name', 'create_date', 'created_by', 'update_date', 'updated_by', 'parent_ticket_id', 'assignee', 'owner', 'due_date', 'rank', 'estimation', 'spent', 'workgroup') to ('5179881', 'Управление релизами изменениями', 'Задача', 'Закрыто', 'Normal', 'Средний', 'PPRC-2516', '[PPPL] [FE] - Сделать автозаполнение формы данными из парсинга json', '2024-09-24 12:22:30.450001', 'Е. Б.', '2024-10-23 07:00:42.070146', 'Е. Ш.', '4933112', 'Е. Ш.', 'Е. Б.', nan, '0|qm0rdc:', '57600', nan, 'Новая функциональность')
Data columns (total 1 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   Table 1  2028 non-null   object
dtypes: object(1)
memory usage: 618.2+ KB
None

First 5 rows:
                                                                                                                                                                                                                                                                                                                   Table 1
entity_id area                type    status       state  priority    ticket_number name                                               create_date                created_by update_date                updated_by parent_ticket_id assignee owner due_date rank       estimation spent workgroup               resolution
94297     Система.Таск-трекер Дефект  Закрыто      Normal Средний     PPTS-1965     [FE] Бэклог. Кастомизация колонок. Кастомизация... 2023-03-16 16:59:00.000000 А. К.      2024-09-10 11:20:09.193785 А. К.      72779            А. К.    А. К. NaN      0|qzzywk:  60         NaN   NaN                         Готово
102481    Система.Ошибки      История Закрыто      Normal Критический PPIN-1175     [ГенераторДокументов] Интеграция со Система.Ген... 2023-05-12 13:33:55.918127 А. З.      2024-08-06 19:30:16.692683 NaN        3488105          А. Е.    А. Е. NaN      0|qv7n1c:y 432000     NaN   Новая функциональность      Готово
1805925   Система.Таск-трекер Дефект  Тестирование Normal Высокий     PPTS-3189     [FE] История изменений. Пустые строки в истории... 2023-07-12 09:36:04.479760 А. К.      2024-11-05 15:02:00.900484 А. К.      NaN              А. К.    А. К. NaN      0|qzsklw:  60         NaN   NaN                            NaN
1934905   Система.Таск-трекер Дефект  Закрыто      Normal Средний     PPTS-3383     [FE] Зависимые поля. Тип реакции disable НЕ раб... 2023-08-04 11:32:25.829919 А. Д.      2024-08-13 11:46:20.165757 А. К.      NaN              А. К.    Я. П. NaN      0|qzh3e8:  NaN        NaN   NaN                         Готово

Statistical Summary:
       Table 1
count     2028
unique       5
top     Готово
freq      1926


/home/dukhanin/agile_new/analysis/data_for_spb_hakaton_entities/sprints-Table 1.csv
<class 'pandas.core.frame.DataFrame'>
MultiIndex: 7 entries, ('sprint_name', 'sprint_status', 'sprint_start_date', 'sprint_end_date') to ('Спринт 2024.3.6.NPP Shared Sprint', 'Закрыт', '2024-09-11 19:00:00.000000', '2024-09-24 19:00:00.000000')
Data columns (total 1 columns):
 #   Column   Non-Null Count  Dtype 
---  ------   --------------  ----- 
 0   Table 1  7 non-null      object
dtypes: object(1)
memory usage: 1.3+ KB
None

First 5 rows:
                                                                                                                                                 Table 1
sprint_name                       sprint_status sprint_start_date          sprint_end_date                                                    entity_ids
Спринт 2024.3.1.NPP Shared Sprint Закрыт        2024-07-03 19:00:00.000000 2024-07-16 19:00:00.000000  {4449728,4450628,4451563,4451929,4452033,44522...
Спринт 2024.3.2.NPP Shared Sprint Закрыт        2024-07-17 19:00:00.000000 2024-07-30 19:00:00.000000  {4506286,4429413,4327418,4370041,4525683,43267...
Спринт 2024.3.3.NPP Shared Sprint Закрыт        2024-07-31 19:00:00.000000 2024-08-13 19:00:00.000000  {4646403,4176602,4555571,4497495,4340795,46178...
Спринт 2024.3.4.NPP Shared Sprint Закрыт        2024-08-14 19:00:00.000000 2024-08-27 19:00:00.000000  {4805777,4596004,4594168,4523718,4579094,46853...

Statistical Summary:
           Table 1
count            7
unique           7
top     entity_ids
freq             1



<class 'pandas.core.frame.DataFrame'>
MultiIndex: 64180 entries, ('entity_id', 'history_property_name', 'history_date', 'history_version', 'history_change_type', 'history_change', 'Столбец1') to ('5179881', 'Статус', '10/23/24 7:00', '12', 'FIELD_CHANGED', 'inProgress -> closed', nan)
Data columns (total 1 columns):
 #   Column   Non-Null Count  Dtype  
---  ------   --------------  -----  
 0   Table 1  0 non-null      float64
dtypes: float64(1)
memory usage: 2.4+ MB
None

First 5 rows:
                                                                                          
                                                                                        /home/dukhanin/agile_new/analysis/data_for_spb_hakaton_entities/history-Table 1.csv                                                        Table 1
entity_id history_property_name  history_date  history_version history_change_type history_change                                     Столбец1      NaN
94297     Время решения 3ЛП ФАКТ 9/10/24 11:17 1               FIELD_CHANGED       <empty> -> 2024-09-10 11:17:06.680223              NaN           NaN
          Время решения (ФАКТ)   9/10/24 11:17 1               FIELD_CHANGED       <empty> -> 2024-09-10 11:17:06.680223              NaN           NaN
          Исполнитель            7/13/23 11:07 1               FIELD_CHANGED       user409017mail@mail.com -> user408045mail@mail.com NaN           NaN
NaN       NaN                    NaN           NaN             NaN                 NaN                                                NaN           NaN

Statistical Summary:
       Table 1
count      0.0
mean       NaN
std        NaN
min        NaN
25%        NaN
50%        NaN
75%        NaN
max        NaN


Команда, получили от экспертов объяснение колонок, направляем

GUID задачи
Название проектной области
Тип задачи
Номер задачи
Название
Когда создана
Кем создана
Когда обновлена последний раз
Кем обновлена последний раз
Номер родительской задачи
На кого назначена
Автор задачи
Срок исполнения
Приоритет
Оценка в часах
Сколько времени списано на задачу
Рабочая группа
Резолюция по задаче

——————-

history_property_name - параметр, по которому произошло изменение 
history_date - дата изменения 
history_version - весия изменения 
history_change_type - тип изменения
history_change - изменение, по которому можно объединить изменения)