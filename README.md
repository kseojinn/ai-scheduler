# 🤖 AI 시간표 최적화 시스템

시뮬레이티드 어닐링과 유전 알고리즘을 결합한 지능형 시간표 생성 시스템

## ✨ 주요 기능

- **하이브리드 AI 알고리즘**: 시뮬레이티드 어닐링 + 유전 알고리즘
- **4가지 최적화 전략**: 오전회피, 점심확보, 공강최대화, 요일분산
- **실시간 웹 인터페이스**: 과목 자동완성 및 시각적 시간표
- **스마트 제약조건**: 15-18학점, 시간충돌 방지, 중복 과목 제거

## 🚀 빠른 시작

```bash
git clone https://github.com/kseojinn/ai-scheduler.git
cd ai-scheduler
pip install flask
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 📁 파일 구조

```
ai-scheduler/
├── app.py              # Flask 애플리케이션
├── courses.json        # 과목 데이터
├── templates/
│   └── index.html      # 웹 인터페이스
└── README.md
```

## 🎯 최적화 유형

- **☀️ 오전 수업 회피**: 1-3교시 최소화
- **🍽️ 점심시간 확보**: 4-6교시 공강
- **⏰ 최대 공강**: 자유시간 극대화
- **📅 요일 분산**: 수업을 여러 요일에 분산

## 🕒 지원 시간

1교시 (09:00) ~ 15교시 (22:45)

## 👨‍💻 개발자

Seojin Kang
