# Report template

Adapt the headings to the user's language. Korean is shown first and English in parentheses. Drop sections that do not apply. Keep the whole report to about one page plus figures.

```markdown
# 실험 결과 보고 (Experiment results): <짧은 제목>

## 요약 (Summary)
- <가장 중요한 결과 1문장: 효과의 크기와 불확실성 포함. 예: "제안기법은 baseline보다 정확도가 평균 0.0287 높았다 (95% CI 0.0152–0.0421, n=4 vs 5)" (숫자와 자릿수는 summary.md 그대로)>
- <두 번째 결과>
- <주의할 점 1개: 작은 n, 이상치, 데이터셋 간 차이 등>

## 데이터 (Data)
- 파일: <파일명> · 행 <N>개 · 조건: <조건 열과 값> · 반복: <seed 등, 조건당 n>
- 지표: <지표 목록과 방향 (높을수록 좋음/낮을수록 좋음)>
- 제외·결측: <몇 개, 어디서, 왜>

## 결과 (Results)

### <지표 1>
<summary.md의 표를 그대로 옮기되, 필요한 열만. 여러 번 실행했다면 어느 부분집합인지 표시>

![<그림 설명>](figs/<file>.png)
*그림 1. <무엇을 그렸는지>. 오차막대: <95% CI / SD / SEM>, 조건당 n = <n>.*

<관찰 2–3문장. summary.json의 숫자만 사용.>

### 비교 (Comparisons)
| 비교 | 평균 차이 [95% CI] | p (Holm) | Cohen's d |
|---|---|---|---|

## 해석과 한계 (Interpretation and limitations)
- 해석: <데이터가 보여주는 것과 구분해서 '가능성'으로 서술>
- 한계: <작은 n, 다중비교, 단일 데이터셋, 하이퍼파라미터 미조정 등>

## 다음 단계 제안 (Suggested next steps)
- <추가 seed, 다른 데이터셋, 이상치 run 재실행 등>
```

## Wording guide

| Instead of | Write |
|---|---|
| "B is significantly better" (p from 3 seeds, uncorrected) | "B was higher by 0.03 (95% CI 0.01–0.05); with n=3 per group this is preliminary" |
| "B improves accuracy by 3%" (absolute 0.03) | "by 0.03 (3 percentage points)", and say whether you mean absolute or relative |
| "No difference" (p = 0.2) | "No clear difference detected (diff 0.004, 95% CI −0.003–0.011)" |
| Removing a strange run without comment | "Run at row 15 (148.2 min, about 2x the others) was flagged as an outlier; results with and without it are shown" |
