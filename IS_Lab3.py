import csv
import random
import copy
from tabulate import tabulate

class Auditorium:
    def __init__(self, auditorium_id, capacity):
        self.id = auditorium_id
        self.capacity = int(capacity)

class Group:
    def __init__(self, group_number, student_amount, subgroups):
        self.number = group_number
        self.size = int(student_amount)
        self.subgroups = subgroups.strip('"').split(';') if subgroups else []

class Lecturer:
    def __init__(self, lecturer_id, name, subjects_can_teach, types_can_teach, max_hours_per_week):
        self.id = lecturer_id
        self.name = name
        self.subjects_can_teach = [s.strip() for s in subjects_can_teach.split(';')] if subjects_can_teach else []
        self.types_can_teach = [t.strip() for t in types_can_teach.split(';')] if types_can_teach else []
        self.max_hours_per_week = int(max_hours_per_week)

class Subject:
    def __init__(self, subject_id, name, group_id, num_lectures, num_practicals, requires_subgroups, week_type):
        self.id = subject_id
        self.name = name
        self.group_id = group_id
        self.num_lectures = int(num_lectures)
        self.num_practicals = int(num_practicals)
        self.requires_subgroups = True if requires_subgroups.lower() == 'yes' else False
        self.week_type = week_type.lower()  # 'both', 'even', 'odd'

def read_auditoriums(filename):
    auditoriums = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            auditoriums.append(Auditorium(row['auditoriumID'], row['capacity']))
    return auditoriums

def read_groups(filename):
    groups = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            groups.append(Group(row['groupNumber'], row['studentAmount'], row['subgroups']))
    return groups

def read_lecturers(filename):
    lecturers = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            lecturers.append(Lecturer(
                row['lecturerID'],
                row['lecturerName'],
                row['subjectsCanTeach'],
                row['typesCanTeach'],
                row['maxHoursPerWeek']
            ))
    return lecturers

def read_subjects(filename):
    subjects = []
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            subjects.append(Subject(
                row['id'],
                row['name'],
                row['groupID'],
                row['numLectures'],
                row['numPracticals'],
                row['requiresSubgroups'],
                row['weekType']
            ))
    return subjects

auditoriums = read_auditoriums('auditoriums.csv')
groups = read_groups('groups.csv')
lecturers = read_lecturers('lecturers.csv')
subjects = read_subjects('subjects.csv')

valid_group_ids = set(group.number for group in groups)
filtered_subjects = []
for subject in subjects:
    if subject.group_id in valid_group_ids:
        filtered_subjects.append(subject)
subjects = filtered_subjects

subject_ids = set(subject.id for subject in subjects)
lecturer_subjects = set()
for lecturer in lecturers:
    lecturer_subjects.update(lecturer.subjects_can_teach)

missing_subjects = subject_ids - lecturer_subjects

DAYS = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', "П'ятниця"]
PERIODS = ['1', '2', '3', '4']  # Періоди у день
TIME_SLOTS = [(day, period) for day in DAYS for period in PERIODS]

class Lesson:
    def __init__(self, subject, lesson_type, group, subgroup=None):
        self.subject = subject
        self.type = lesson_type
        self.group = group
        self.subgroup = subgroup
        self.time_slot = None
        self.auditorium = None
        self.lecturer = None

class Schedule:
    def __init__(self):
        self.timetable = {time_slot: [] for time_slot in TIME_SLOTS}
        self.fitness = None

    def calculate_fitness(self):
        penalty = self._calculate_fitness_for_week()
        penalty += self._calculate_soft_constraints()
        if penalty < 0:
            penalty = 0
        self.fitness = 1 / (1 + penalty)

    def _calculate_fitness_for_week(self):
        penalty = 0
        for group in groups:
            subgroups = group.subgroups if group.subgroups else [None]
            for subgroup in subgroups:
                schedule_list = []
                for time_slot, lessons in self.timetable.items():
                    for lesson in lessons:
                        if lesson.group.number == group.number and lesson.subgroup == subgroup:
                            schedule_list.append(time_slot)
                schedule_sorted = sorted(schedule_list, key=lambda x: (DAYS.index(x[0]), int(x[1])))
                for i in range(len(schedule_sorted) - 1):
                    day1, period1 = schedule_sorted[i]
                    day2, period2 = schedule_sorted[i + 1]
                    if day1 == day2:
                        gaps = int(period2) - int(period1) - 1
                        if gaps > 0:
                            penalty += gaps
        for lecturer in lecturers:
            schedule_list = []
            for time_slot, lessons in self.timetable.items():
                for lesson in lessons:
                    if lesson.lecturer and lesson.lecturer.id == lecturer.id:
                        schedule_list.append(time_slot)
            schedule_sorted = sorted(schedule_list, key=lambda x: (DAYS.index(x[0]), int(x[1])))
            for i in range(len(schedule_sorted) - 1):
                day1, period1 = schedule_sorted[i]
                day2, period2 = schedule_sorted[i + 1]
                if day1 == day2:
                    gaps = int(period2) - int(period1) - 1
                    if gaps > 0:
                        penalty += gaps
            hours_assigned = len(schedule_list)
            max_hours = lecturer.max_hours_per_week
            if hours_assigned > max_hours:
                penalty += (hours_assigned - max_hours) * 2
        return penalty

    def _calculate_soft_constraints(self):
        penalty = 0
        for subject in subjects:
            group = next((g for g in groups if g.number == subject.group_id), None)
            if not group:
                continue
            subgroups = group.subgroups if group.subgroups else [None]
            for subgroup in subgroups:
                scheduled_lectures = 0
                scheduled_practicals = 0
                required_lectures = subject.num_lectures // len(subgroups) if subject.requires_subgroups else subject.num_lectures
                required_practicals = subject.num_practicals // len(subgroups) if subject.requires_subgroups else subject.num_practicals
                for time_slot, lessons in self.timetable.items():
                    for lesson in lessons:
                        if (lesson.subject.id == subject.id and
                            lesson.group.number == group.number and
                            lesson.subgroup == subgroup):
                            if lesson.type == 'Лекція':
                                scheduled_lectures += 1
                            elif lesson.type == 'Практика':
                                scheduled_practicals += 1
                diff_lectures = scheduled_lectures - required_lectures
                diff_practicals = scheduled_practicals - required_practicals
                penalty += abs(diff_lectures) * 2  #
                penalty += abs(diff_practicals) * 2
        return penalty

def get_possible_lecturers(lesson):
    possible = [lecturer for lecturer in lecturers if
                lesson.subject.id in lecturer.subjects_can_teach and
                lesson.type in lecturer.types_can_teach]
    return possible

def is_conflict(lesson, time_slot, timetable):
    for existing_lesson in timetable[time_slot]:
        if lesson.lecturer and existing_lesson.lecturer and existing_lesson.lecturer.id == lesson.lecturer.id:
            return True
        if lesson.auditorium and existing_lesson.auditorium and existing_lesson.auditorium.id == lesson.auditorium.id:
            if lesson.type != 'Лекція' or existing_lesson.type != 'Лекція':
                return True
        if lesson.group.number == existing_lesson.group.number:
            if lesson.subgroup == existing_lesson.subgroup:
                return True
            if not lesson.subgroup or not existing_lesson.subgroup:
                return True
    return False

POPULATION_SIZE = 50
GENERATIONS = 100

def create_initial_population():
    population = []
    for _ in range(POPULATION_SIZE):
        schedule = Schedule()
        for subject in subjects:
            group = next((g for g in groups if g.number == subject.group_id), None)
            if not group:
                continue
            # Лекції
            lectures_total = subject.num_lectures
            for _ in range(lectures_total):
                lesson = Lesson(subject, 'Лекція', group)
                possible_lecturers = get_possible_lecturers(lesson)
                if not possible_lecturers:
                    continue
                lecturer = random.choice(possible_lecturers)
                lesson.lecturer = lecturer
                suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= group.size]
                if not suitable_auditoriums:
                    continue
                auditorium = random.choice(suitable_auditoriums)
                lesson.auditorium = auditorium
                assigned = assign_randomly(lesson, schedule)
                if not assigned:
                    continue
            # Практичні
            pract_total = subject.num_practicals
            if subject.requires_subgroups and group.subgroups:
                num_practicals_per_subgroup = pract_total // len(group.subgroups)
                for subgroup in group.subgroups:
                    for _ in range(num_practicals_per_subgroup):
                        lesson = Lesson(subject, 'Практика', group, subgroup)
                        possible_lecturers = get_possible_lecturers(lesson)
                        if not possible_lecturers:
                            continue
                        lecturer = random.choice(possible_lecturers)
                        lesson.lecturer = lecturer
                        subgroup_size = group.size // len(group.subgroups)
                        suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= subgroup_size]
                        if not suitable_auditoriums:
                            continue
                        auditorium = random.choice(suitable_auditoriums)
                        lesson.auditorium = auditorium
                        assigned = assign_randomly(lesson, schedule)
                        if not assigned:
                            continue
            else:
                for _ in range(pract_total):
                    lesson = Lesson(subject, 'Практика', group)
                    possible_lecturers = get_possible_lecturers(lesson)
                    if not possible_lecturers:
                        continue
                    lecturer = random.choice(possible_lecturers)
                    lesson.lecturer = lecturer
                    suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= group.size]
                    if not suitable_auditoriums:
                        continue
                    auditorium = random.choice(suitable_auditoriums)
                    lesson.auditorium = auditorium
                    assigned = assign_randomly(lesson, schedule)
                    if not assigned:
                        continue
        schedule.calculate_fitness()
        population.append(schedule)
    return population

def assign_randomly(lesson, schedule):
    assigned = False
    available_time_slots = TIME_SLOTS.copy()
    random.shuffle(available_time_slots)
    for time_slot in available_time_slots:
        if not is_conflict(lesson, time_slot, schedule.timetable):
            lesson.time_slot = time_slot
            schedule.timetable[time_slot].append(copy.deepcopy(lesson))
            assigned = True
            break
    return assigned

def selection(population):
    population.sort(key=lambda x: x.fitness, reverse=True)
    selected = population[:int(0.2 * len(population))]  # Вибір топ 20%
    return selected

def crossover(parent1, parent2):
    child = Schedule()
    for time_slot in TIME_SLOTS:
        if random.random() < 0.5:
            source_lessons = parent1.timetable[time_slot]
        else:
            source_lessons = parent2.timetable[time_slot]
        for lesson in source_lessons:
            if not is_conflict(lesson, time_slot, child.timetable):
                child.timetable[time_slot].append(copy.deepcopy(lesson))
    child.calculate_fitness()
    return child

def mutate(schedule):
    mutation_rate = 0.1
    if random.random() < mutation_rate:
        add_random_lesson(schedule.timetable)
    if random.random() < mutation_rate:
        remove_random_lesson(schedule.timetable)
    for time_slot in TIME_SLOTS:
        if schedule.timetable[time_slot]:
            for lesson in schedule.timetable[time_slot][:]:
                if random.random() < mutation_rate:
                    original_time_slot = lesson.time_slot
                    new_time_slot = random.choice(TIME_SLOTS)
                    if new_time_slot == original_time_slot:
                        continue
                    if not is_conflict(lesson, new_time_slot, schedule.timetable):
                        schedule.timetable[original_time_slot].remove(lesson)
                        lesson.time_slot = new_time_slot
                        schedule.timetable[new_time_slot].append(lesson)
    schedule.calculate_fitness()

def add_random_lesson(timetable):
    subject = random.choice(subjects)
    group = next((g for g in groups if g.number == subject.group_id), None)
    if not group:
        return
    lesson_type = random.choice(['Лекція', 'Практика'])
    lessons_to_add = []
    if lesson_type == 'Практика' and subject.requires_subgroups and group.subgroups:
        for subgroup in group.subgroups:
            lesson = Lesson(subject, lesson_type, group, subgroup)
            lessons_to_add.append(lesson)
    else:
        lesson = Lesson(subject, lesson_type, group)
        lessons_to_add.append(lesson)
    for lesson in lessons_to_add:
        possible_lecturers = get_possible_lecturers(lesson)
        if not possible_lecturers:
            return
        lecturer = random.choice(possible_lecturers)
        lesson.lecturer = lecturer
        if lesson.subgroup:
            students = group.size // len(group.subgroups)
            suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= students]
        else:
            students = group.size
            suitable_auditoriums = [aud for aud in auditoriums if aud.capacity >= students]
        if not suitable_auditoriums:
            return
        auditorium = random.choice(suitable_auditoriums)
        lesson.auditorium = auditorium
    available_time_slots = TIME_SLOTS.copy()
    random.shuffle(available_time_slots)
    for time_slot in available_time_slots:
        conflict = False
        for lesson in lessons_to_add:
            if is_conflict(lesson, time_slot, timetable):
                conflict = True
                break
        if not conflict:
            for lesson in lessons_to_add:
                lesson.time_slot = time_slot
                timetable[time_slot].append(copy.deepcopy(lesson))
            break

def remove_random_lesson(timetable):
    all_lessons = [lesson for lessons in timetable.values() for lesson in lessons]
    if not all_lessons:
        return
    lesson_to_remove = random.choice(all_lessons)
    lessons_to_remove = []
    if lesson_to_remove.subgroup:
        for lessons in timetable.values():
            for lesson in lessons:
                if (lesson.subject.id == lesson_to_remove.subject.id and
                    lesson.group.number == lesson_to_remove.group.number and
                    lesson.type == lesson_to_remove.type):
                    lessons_to_remove.append(lesson)
    else:
        lessons_to_remove.append(lesson_to_remove)
    for lesson in lessons_to_remove:
        timetable[lesson.time_slot].remove(lesson)

def genetic_algorithm():
    population = create_initial_population()
    for generation in range(GENERATIONS):
        selected = selection(population)
        new_population = []
        elite_size = int(0.1 * POPULATION_SIZE)
        elites = selected[:elite_size]
        new_population.extend(copy.deepcopy(elites))
        while len(new_population) < POPULATION_SIZE:
            parent1, parent2 = random.sample(selected, 2)
            child = crossover(parent1, parent2)
            mutate(child)
            new_population.append(child)
        population = new_population
        best_fitness = max(schedule.fitness for schedule in population)
        if best_fitness == 1.0:
            break
    best_schedule = max(population, key=lambda x: x.fitness)
    return best_schedule

def print_schedule(schedule):
    table = []
    headers = ['Пара/День'] + DAYS
    for period in PERIODS:
        row = [f"Пара {period}"]
        for day in DAYS:
            lessons = [lesson for lesson in schedule.timetable[(day, period)]]
            if lessons:
                lesson_strs = []
                for lesson in lessons:
                    group = lesson.group.number
                    if lesson.subgroup:
                        group += f" ({lesson.subgroup})"
                    lesson_info = f"{lesson.subject.name}\n{lesson.type}\n{lesson.lecturer.name}\nАудиторія: {lesson.auditorium.id}"
                    lesson_strs.append(f"{group}: {lesson_info}")
                cell = "\n---\n".join(lesson_strs)
            else:
                cell = "-"
            row.append(cell)
        table.append(row)

    print("\nНайкращий розклад:\n")
    print(tabulate(table, headers=headers, tablefmt="fancy_grid", stralign="left"))

if __name__ == "__main__":
    best_schedule = genetic_algorithm()
    print_schedule(best_schedule)