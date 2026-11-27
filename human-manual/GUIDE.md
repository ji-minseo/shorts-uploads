# 인간 사용설명서 — 제작 가이드 (자동화용)

인스타 계정: @kuru.observes (계정 이름: 쿠루의 인간 관찰일지). 시리즈 제목은 '인간 사용설명서'. 캡션 해시태그는 정확히 이 4개만: #인스타툰 #심리학 #심리툰 #생활과학 (인스타 규정상 5개 이하. 다른 해시태그 추가 금지).

외계인 보호자 '쿠루'가 인간을 처음 입양해서 키우며 '인간 사용설명서'를 펼쳐보는 심리학·생활과학 손그림 인스타툰.
귀여운 세계관 + **실제로 맞는** 심리학/생활과학 지식.

## 캐릭터 (그림체 고정 — render.py가 그림)
- **쿠루 (alien)**: 길쭉한 민트색 달걀형 외눈 외계인. 무심한 표정(작은 동공, 일자 입). 존댓말·보고서 말투("~입니다", "~합니까?"). 감정 표현이 적지만 인간을 아낌(마지막 장 무표정 + 하트).
- **인간 (bed / human)**: 줄무늬 보라 파자마, 까만 헝클어진 머리, 더듬이 같은 삐친 머리카락. 반말, 감정 과잉.

## 한 화 구성 (9장, 1080×1350)
1. `cover` — 표지 (제목 = 이번 화 질문)
2. `comic` — 관찰일지: 인간의 이상 행동 장면
3. `comic` — 사건이 커지는 장면 / 인간 대사
4. `comic` — 쿠루가 분석하며 이해 못함 → caption "보호자는 (다시) 설명서를 펼쳤다."
5~7. `manual` p.1~3 — 설명서: 이유 3가지 (본문 + 낙서 doodle + 쿠루 한마디 note)
8. `solution` — 보호자용 처방전 (연구 근거 1개, 저자·연도 표기)
9. `ending` — 관찰 결론 + 다음 화 예고(next)

## 사실 확인 규칙 (중요)
- 설명서 내용과 처방전은 **반드시 웹 검색으로 확인한 실제 연구/개념**만 쓴다. 기억에 의존 금지.
- 처방전에는 실제 논문 1개를 (저자 외, 연도)로 표기하고, 캡션에 저널명까지 적는다.
- 과장 금지: "~라는 연구도 있다", "~하기도 한다"처럼 근거 수준에 맞게 쓴다. 재현 논란이 큰 효과(예: 자아고갈, 파워포즈)는 피한다.
- 의학적 진단·치료 조언은 하지 않는다.

## 문장 규칙
- manual body: 한 줄 최대 약 20자, 최대 7줄. heading: 최대 약 22자 (넘으면 자동으로 글자가 작아지지만 짧을수록 좋음).
- 말풍선 bubble: 한 줄 최대 약 14자(w 460 기준), w를 늘리면 더 길게 가능(w 780이면 약 17자). 줄바꿈은 `\n`.
- note(쿠루 한마디): 2줄, 줄당 8자 내외. 웃기게.
- label(comic 상단): "관찰일지 DAY NN · 시간/장소". DAY 숫자는 화마다 조금씩 늘린다.

## JSON 형식 — episodes/epNN.json
```json
{"ep": 3, "title": "질문\n두 줄", "next": "다음 화 질문\n두 줄", "slides": [ ... 9개 ... ]}
```
슬라이드별 필드:
- cover: `elements`
- comic: `label`, `elements`, (선택) `caption`
- manual: `page`, `heading`, `body`, `doodle`(요소 배열), `note`
- solution: `heading`("보호자용 처방전"), `body`, `elements`
- ending: `log`("관찰 결론:\n..."), `elements`

### 요소(elements / doodle) 카탈로그
좌표는 슬라이드 전체 기준(px). (x,y)는 캐릭터의 **발 아래 중심**.
- `alien` {x,y,s, mood: calm|confused|shock|reading|proud|love, hold: none|clipboard|book|note}
  - 높이 ≈ 470×s (더듬이 포함). note는 "내일 할 일" 쪽지 고정이므로 다른 화에선 none 권장.
- `bed` {x,y,s, eyes: closed|sleepy|wide|shock, kick: true|false} — 침대에 누운 인간. 폭 ≈ 660×s, 높이 ≈ 330×s(kick이면 ≈ 520×s)
- `human` {x,y,s, pose: stand|cheer|slump|walk|sit, eyes: wide|happy|sad|shock|blank|sleepy|closed, hold: none|phone|bag|money|coin|cup|heart|box…(icon 이름)}
  - 높이 ≈ 460×s (cheer ≈ 500×s, sit ≈ 400×s)
- `bubble` {x,y,w,text, tail:[x,y] 선택, kind: speech|narr} — (x,y)=말풍선 중심. 꼬리는 아래쪽에서 tail 지점으로.
- `shout` {x,y,text} — 노란 폭발 효과음 (폭 약 580)
- `zzz` {x,y}
- `icon` {name, x,y,s} — phone, bag, box(택배), coin, money, heart, clock, cloud, rain, lightning, star, cup, battery, dopamine, pillow, calendar
- `brain` {x,y,r, face: calm|busy|evil|sleepy}
- `arrow` {x1,y1,x2,y2}
- `box` {x,y,w,h,text, fill, size} — 손그림 라벨 상자
- `label` {x,y,text,size,rot} — 손글씨 텍스트

### 안전 영역 (겹침 방지)
- comic 패널 내부: x 80~1000, y 190~1190. 캡션은 y 1275에 자동.
- 캐릭터 발은 comic에선 y 1150~1170, cover/solution에선 y 1110~1150.
- manual: 본문은 y 300~720 사용. **doodle은 y 730~1030**, 단 x 480~840 & y 1030 이하는 쿠루 note 말풍선 자리, x 850 이상 & y 960 이하는 미니 쿠루 자리 → 비워둘 것.
- ending: 쿠루 y 910, s 1.0 고정 추천.
- 말풍선은 캐릭터 머리 위 공간에 두고, 꼬리를 말하는 캐릭터 머리 쪽으로.

## 제작 순서
1. `topics.md`에서 체크 안 된 첫 주제 선택 (그 다음 주제가 이번 화의 `next`)
2. 웹 검색으로 근거 연구 2~3개 확인
3. `episodes/epNN.json` 작성 (EP.01, EP.02를 예시로 참고)
4. `python3 render.py episodes/epNN.json` → `out/epNN/` 에 slide01~09.jpg + overview.jpg
5. **overview.jpg와 각 슬라이드를 직접 열어서 검사**: 글자 잘림, 말풍선이 캐릭터/글자 가림, 요소 겹침, 테두리 밖으로 삐져나감 → JSON 좌표 수정 후 재렌더. 문제 없을 때까지 반복.
6. `out/epNN/caption.txt` 작성 (EP.01, EP.02 캡션 형식 그대로: 제목, 상황 한 줄, ✔ 3개, 💊 처방 + 출처, 참여 유도 질문, 마지막 줄 해시태그 4개 고정: #인스타툰 #심리학 #심리툰 #생활과학)
7. topics.md에 체크, 커밋 & 푸시
