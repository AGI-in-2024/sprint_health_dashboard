# Формулы расчета здоровья спринта

## Слайд 1: Базовые компоненты оценки (Общий вес = 100%)
- Процент задач "To Do" (10%): Штраф за превышение 15% от общего объема
- Равномерность выполнения (18%): Оценка распределения изменений статусов
- Процент завершения (20%): Соотношение выполненных задач к общему количеству

## Слайд 2: Дополнительные метрики (Общий вес = 100%)
- Стабильность бэклога (12%): Штраф за изменения после начала спринта
- Соответствие burndown (12%): Отклонение от идеальной кривой выгорания
- Командное взаимодействие (5%): Оценка распределения задач между участниками
- Старение задач (5%): Штраф за превышение среднего времени выполнения

## Слайд 3: Расширенная оценка
- Комплексный показатель = Σ(Вес_компонента × Оценка_компонента)
- Нормализация: Все оценки приводятся к шкале [0, 1]
- Интерпретация:
  * 0.8 - 1.0: Отличное состояние спринта
  * 0.6 - 0.8: Нормальное состояние
  * < 0.6: Требуется внимание 