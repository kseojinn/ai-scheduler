from flask import Flask, render_template, request, jsonify
import json
import random
import math
import copy
from collections import defaultdict

app = Flask(__name__)

# 시간표 데이터 로드
with open('courses.json', 'r', encoding='utf-8') as f:
    course_data = json.load(f)

COURSES = course_data['courses']

# 시간 슬롯 매핑
TIME_SLOTS = {
    '1': (9, 0, 9, 50),
    '2': (9, 55, 10, 45),
    '3': (10, 50, 11, 40),
    '4': (11, 55, 12, 45),
    '5': (12, 50, 13, 40),
    '6': (13, 45, 14, 35),
    '7': (14, 40, 15, 30),
    '8': (15, 35, 16, 25),
    '9': (16, 30, 17, 25),
    '10': (17, 40, 18, 30),
    '11': (18, 30, 19, 20),
    '12': (19, 20, 20, 10),
    '13': (20, 15, 21, 5),
    '14': (21, 5, 21, 55),
    '15': (21, 55, 22, 45)
}

DAYS = ['월', '화', '수', '목', '금']

def parse_schedule(schedule_str):
    """스케줄 문자열을 파싱하여 요일과 시간 정보 반환"""
    if not schedule_str or schedule_str.strip() == '':
        return []
    
    day_map = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4}
    schedule_info = []
    
    day = schedule_str[0]
    if day in day_map:
        time_part = schedule_str[1:]
        if '-' in time_part:
            start_time, end_time = time_part.split('-')
            try:
                start = int(start_time)
                end = int(end_time)
                for time_slot in range(start, end + 1):
                    schedule_info.append((day_map[day], time_slot))
            except ValueError:
                pass
    
    return schedule_info

def has_conflict(schedule1, schedule2):
    """두 스케줄 간 충돌 여부 확인"""
    slots1 = parse_schedule(schedule1)
    slots2 = parse_schedule(schedule2)
    
    for slot1 in slots1:
        for slot2 in slots2:
            if slot1 == slot2:
                return True
    return False

class TimetableOptimizer:
    def __init__(self, courses, excluded_courses, optimization_type):
        self.courses = [c for c in courses if c['course_name'] not in excluded_courses]
        self.optimization_type = optimization_type
        self.min_credits = 15
        self.max_credits = 18
        
    def create_random_timetable(self):
        """랜덤 시간표 생성"""
        selected = []
        total_credits = 0
        used_course_names = set()
        
        # 필수 과목부터 선택 (단, 점심시간 최적화일 때는 점심시간 피함)
        required_courses = [c for c in self.courses if c['category'] == '교필']
        if self.optimization_type == 'lunch_time':
            # 점심시간과 겹치지 않는 필수과목 우선 선택
            required_courses = sorted(required_courses, 
                                    key=lambda x: self._has_lunch_conflict(x['schedule']))
        
        for course in required_courses:
            if (total_credits + course['credits'] <= self.max_credits and 
                course['course_name'] not in used_course_names and
                not any(has_conflict(course['schedule'], s['schedule']) for s in selected)):
                selected.append(course)
                total_credits += course['credits']
                used_course_names.add(course['course_name'])
        
        # 나머지 과목 선택
        other_courses = [c for c in self.courses if c['category'] != '교필']
        random.shuffle(other_courses)
        
        # 점심시간 최적화의 경우 점심시간 피하는 과목 우선
        if self.optimization_type == 'lunch_time':
            other_courses = sorted(other_courses, 
                                 key=lambda x: self._has_lunch_conflict(x['schedule']))
        
        for course in other_courses:
            if (total_credits >= self.min_credits and total_credits + course['credits'] > self.max_credits):
                continue
            if (course['course_name'] not in used_course_names and
                not any(has_conflict(course['schedule'], s['schedule']) for s in selected)):
                selected.append(course)
                total_credits += course['credits']
                used_course_names.add(course['course_name'])
                
                if total_credits >= self.max_credits:
                    break
        
        return selected if total_credits >= self.min_credits else []
    
    def _has_lunch_conflict(self, schedule_str):
        """점심시간(4-6교시)와 겹치는지 확인"""
        slots = parse_schedule(schedule_str)
        for day, time in slots:
            if 4 <= time <= 6:  # 점심시간
                return True
        return False
    
    def calculate_fitness(self, timetable):
        """적합도 함수"""
        if not timetable:
            return -1000
        
        total_credits = sum(course['credits'] for course in timetable)
        if total_credits < self.min_credits:
            return -1000
        
        # 기본 점수
        score = 0
        
        # 학점 점수 (15-18학점 사이가 최적)
        if self.min_credits <= total_credits <= self.max_credits:
            score += 100
        else:
            score -= abs(total_credits - 17) * 10
        
        # 시간표 분석
        time_grid = [[False] * 16 for _ in range(5)]  # 5일 x 16시간 (1-15교시)
        
        for course in timetable:
            slots = parse_schedule(course['schedule'])
            for day, time in slots:
                if 0 <= day < 5 and 1 <= time <= 15:
                    time_grid[day][time] = True
        
        # 최적화 타입별 점수 계산
        if self.optimization_type == 'morning_avoid':
            # 오전 수업 회피
            morning_classes = sum(sum(time_grid[day][1:4]) for day in range(5))
            score -= morning_classes * 30
            
        elif self.optimization_type == 'lunch_time':
            # 점심시간 확보 (4-6교시)
            lunch_conflicts = 0
            for day in range(5):
                if any(time_grid[day][4:7]):  # 4, 5, 6교시 확인
                    lunch_conflicts += 1
            score -= lunch_conflicts * 40  # 패널티 강화
            
            # 점심시간이 완전히 비어있는 날에 보너스
            free_lunch_days = 0
            for day in range(5):
                if not any(time_grid[day][4:7]) and any(time_grid[day]):  # 수업은 있지만 점심시간은 비어있음
                    free_lunch_days += 1
            score += free_lunch_days * 30
            
        elif self.optimization_type == 'max_free_time':
            # 최대한 많은 공강 확보 - 수정된 로직
            total_class_days = sum(1 for day in range(5) if any(time_grid[day]))
            total_occupied_slots = sum(sum(row) for row in time_grid)
            
            # 수업 있는 날 수를 최소화 (적은 날에 몰아서)
            score += (5 - total_class_days) * 50  # 수업 없는 날당 50점
            
            # 전체 수업 시간 최소화
            score += (75 - total_occupied_slots) * 3  # 비어있는 시간 슬롯당 3점
            
            # 연속된 공강시간 보너스
            for day in range(5):
                if any(time_grid[day]):  # 수업이 있는 날만 확인
                    continuous_free = 0
                    max_continuous_free = 0
                    for time_slot in range(1, 16):
                        if not time_grid[day][time_slot]:
                            continuous_free += 1
                            max_continuous_free = max(max_continuous_free, continuous_free)
                        else:
                            continuous_free = 0
                    score += max_continuous_free * 2  # 연속 공강시간 보너스
            
        elif self.optimization_type == 'distribute_days':
            # 최대한 많은 요일로 분산
            days_used = sum(1 for day in range(5) if any(time_grid[day]))
            score += days_used * 20
            
            # 하루에 너무 많은 수업이 몰리는 것을 방지
            for day in range(5):
                daily_classes = sum(time_grid[day])
                if daily_classes > 6:
                    score -= (daily_classes - 6) * 15
        
        # 추가 보너스
        # 전공 과목 비율
        major_courses = sum(1 for c in timetable if c['category'] in ['전필', '전선'])
        score += major_courses * 5
        
        return score
    
    def mutate(self, timetable):
        """돌연변이 연산"""
        if not timetable:
            return self.create_random_timetable()
        
        new_timetable = copy.deepcopy(timetable)
        used_course_names = {c['course_name'] for c in new_timetable}
        
        # 랜덤하게 변경 방법 선택
        mutation_type = random.choice(['remove', 'add', 'replace'])
        
        if mutation_type == 'remove' and len(new_timetable) > 1:
            # 과목 제거
            new_timetable.pop(random.randint(0, len(new_timetable) - 1))
            
        elif mutation_type == 'add':
            # 과목 추가
            available = [c for c in self.courses 
                        if c['course_name'] not in used_course_names
                        and not any(has_conflict(c['schedule'], s['schedule']) for s in new_timetable)]
            
            if available:
                total_credits = sum(c['credits'] for c in new_timetable)
                valid_courses = [c for c in available if total_credits + c['credits'] <= self.max_credits]
                if valid_courses:
                    new_timetable.append(random.choice(valid_courses))
                    
        elif mutation_type == 'replace' and new_timetable:
            # 과목 교체
            remove_idx = random.randint(0, len(new_timetable) - 1)
            removed_course = new_timetable.pop(remove_idx)
            used_course_names.remove(removed_course['course_name'])
            
            available = [c for c in self.courses 
                        if c['course_name'] not in used_course_names
                        and not any(has_conflict(c['schedule'], s['schedule']) for s in new_timetable)]
            
            if available:
                total_credits = sum(c['credits'] for c in new_timetable)
                valid_courses = [c for c in available if total_credits + c['credits'] <= self.max_credits]
                if valid_courses:
                    new_timetable.append(random.choice(valid_courses))
                else:
                    new_timetable.append(removed_course)  # 원복
            else:
                new_timetable.append(removed_course)  # 원복
        
        return new_timetable
    
    def crossover(self, parent1, parent2):
        """교차 연산"""
        if not parent1 or not parent2:
            return self.create_random_timetable()
        
        # 두 부모의 과목을 합치고 충돌 없는 조합 찾기
        all_courses = parent1 + parent2
        used_names = set()
        child = []
        total_credits = 0
        
        random.shuffle(all_courses)
        
        for course in all_courses:
            if (course['course_name'] not in used_names and
                total_credits + course['credits'] <= self.max_credits and
                not any(has_conflict(course['schedule'], c['schedule']) for c in child)):
                child.append(course)
                used_names.add(course['course_name'])
                total_credits += course['credits']
        
        return child if total_credits >= self.min_credits else parent1
    
    def simulated_annealing_genetic_hybrid(self, population_size=50, generations=100):
        """시뮬레이티드 어닐링과 유전 알고리즘 하이브리드"""
        # 초기 인구 생성
        population = []
        for _ in range(population_size):
            individual = self.create_random_timetable()
            if individual:
                population.append(individual)
        
        if not population:
            return []
        
        # 시뮬레이티드 어닐링 파라미터
        initial_temp = 1000
        final_temp = 1
        cooling_rate = 0.95
        
        best_solutions = []
        
        for generation in range(generations):
            # 현재 온도 계산
            current_temp = initial_temp * (cooling_rate ** generation)
            current_temp = max(current_temp, final_temp)
            
            # 적합도 계산 및 정렬
            fitness_scores = [(self.calculate_fitness(ind), ind) for ind in population]
            fitness_scores.sort(reverse=True, key=lambda x: x[0])
            
            # 최고 해 저장
            if fitness_scores[0][1] not in best_solutions:
                best_solutions.append(fitness_scores[0][1])
            
            # 새로운 인구 생성
            new_population = []
            
            # 엘리트 보존 (상위 20%)
            elite_size = population_size // 5
            for i in range(elite_size):
                new_population.append(fitness_scores[i][1])
            
            # 나머지는 선택, 교차, 돌연변이로 생성
            while len(new_population) < population_size:
                # 토너먼트 선택
                parent1 = self.tournament_selection(population, 3)
                parent2 = self.tournament_selection(population, 3)
                
                # 교차
                if random.random() < 0.8:
                    child = self.crossover(parent1, parent2)
                else:
                    child = random.choice([parent1, parent2])
                
                # 돌연변이
                if random.random() < 0.2:
                    child = self.mutate(child)
                
                # 시뮬레이티드 어닐링 적용
                current_fitness = self.calculate_fitness(child)
                if current_fitness > 0:
                    # 현재 최고와 비교하여 SA 적용
                    best_fitness = fitness_scores[0][0]
                    if (current_fitness > best_fitness or 
                        random.random() < math.exp((current_fitness - best_fitness) / current_temp)):
                        new_population.append(child)
                    else:
                        # 기존 좋은 해 중 하나 선택
                        new_population.append(random.choice([f[1] for f in fitness_scores[:5]]))
                else:
                    # 무효한 해는 다시 생성
                    new_population.append(self.create_random_timetable())
            
            population = new_population
        
        # 최종 결과에서 상위 3개 반환
        final_fitness = [(self.calculate_fitness(sol), sol) for sol in best_solutions]
        final_fitness.sort(reverse=True, key=lambda x: x[0])
        
        return [sol[1] for sol in final_fitness[:3] if sol[0] > 0]
    
    def tournament_selection(self, population, tournament_size):
        """토너먼트 선택"""
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=self.calculate_fitness)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize_timetable():
    data = request.json
    excluded_courses = data.get('excluded_courses', [])
    optimization_type = data.get('optimization_type', 'morning_avoid')
    
    optimizer = TimetableOptimizer(COURSES, excluded_courses, optimization_type)
    best_solutions = optimizer.simulated_annealing_genetic_hybrid()
    
    # 결과 포맷팅
    results = []
    for i, solution in enumerate(best_solutions):
        total_credits = sum(course['credits'] for course in solution)
        fitness = optimizer.calculate_fitness(solution)
        
        # 시간표 그리드 생성
        grid = {}
        for course in solution:
            slots = parse_schedule(course['schedule'])
            for day, time in slots:
                if 0 <= day < 5 and 1 <= time <= 15:
                    day_name = DAYS[day]
                    if day_name not in grid:
                        grid[day_name] = {}
                    grid[day_name][str(time)] = {
                        'course_name': course['course_name'],
                        'professor': course['professor'],
                        'classroom': course['classroom'],
                        'credits': course['credits']
                    }
        
        results.append({
            'id': i + 1,
            'courses': solution,
            'total_credits': total_credits,
            'fitness_score': fitness,
            'grid': grid
        })
    
    return jsonify({
        'success': True,
        'results': results
    })

@app.route('/course_names')
def get_course_names():
    """모든 과목명 반환 (자동완성용)"""
    course_names = list(set(course['course_name'] for course in COURSES))
    course_names.sort()
    return jsonify(course_names)

if __name__ == '__main__':
    app.run(debug=True)
