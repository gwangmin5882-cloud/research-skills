# Grading evidence: experiment task, R01–R06

Reference values were recomputed from input/results.csv (cp949) and input/train_log.csv with the Python standard library: Welch and paired t, Holm, learning-curve statistics, IQR fence, Grubbs, robust z and Mann-Whitney. Every PNG was opened, and crops were zoomed where overlap was suspected.

## R01 (12/14)
- 1 PASS: §2 table: "제안B / 데이터2 / 시드4 의 정확도가 0.1021 ... 학습이 발산·붕괴한 실패 런".
- 2 PASS: crash excluded from the main analysis (n=4) and stated; §6 shows the result with it included (0.6560, −10.35%p, p=0.4955).
- 3 PASS: "제안A / 데이터1 / 시드2 의 정확도 칸이 비어 있음 ... n=4로 분석".
- 4 PASS: §3 and §4 tables are per dataset; "두 데이터셋의 수치를 뭉쳐서 평균 내면 안 되고".
- 5 PASS: §3 table "제안A 데이터1 +2.32%p" (key 0.0232); the paired +1.98%p is also correct for the stated paired method.
- 6 PASS: "데이터2에서는 오히려 −0.27%p로 이득이 없다", CI [−1.11, +0.57]%p, 비유의.
- 7 PASS: 제안B 데이터2 +3.49%p (means) and +3.46%p (paired); with the crash included it is −10.35%p, labelled misleading.
- 8 PASS: n and SD per group (§3); 95% CI, p, Holm p and n per comparison (§4).
- 9 PASS: §7: 제안B 30.24/31.24 ms vs 기준모델 11.85/12.00 ms, "×2.55~2.60".
- 10 PASS: §5: "0.7930 (에폭 17) → 0.7517, −4.13%p ... 전형적인 과적합 패턴".
- 11 FAIL: Checked (1) +2.32%p A−base on 데이터1: correct. (2) paired +3.46%p [1.74, 5.19] for B on 데이터2: correct. (3) 제안B 데이터1 latency 30.24 ms: correct. (4) peak 0.7930 at epoch 17: correct. (5) "모든 방법이 데이터1보다 3~4%p 낮다": WRONG, 제안A is 6.43%p lower (0.8211→0.7568) and 제안B 4.51%p.
- 12 PASS: 4 PNGs; axes labelled (테스트 정확도, 에폭, 추론 지연시간 ms, 정확도 차이); subtitles say "수염 = 평균의 95% 신뢰구간", "음영 = ±1 표준편차", "십자 = ±1 표준편차".
- 13 FAIL: in fig3_learning_curves the right-edge labels "제안B 0.8322" and "제안A 0.8180" overlap each other (zoomed). In fig4 the labels also touch the error-cross arms.
- 14 PASS: no bar charts. Fig1 marks the crash as "축 범위 밖 · 분석 제외", and the 제안B/데이터2 mean is plotted at 0.7944 (crash excluded).

## R02 (13/14)
- 1 PASS: "30행(제안B / 데이터2 / 시드4)의 정확도가 0.1021 ... Grubbs 검정에서 이상치".
- 2 PASS: "포함·제외 두 경우를 모두 제시"; the table has 제안B (30행 제외) and 제안B (전체) rows.
- 3 PASS: "8행(제안A / 데이터1 / 시드2)의 정확도가 비어 있다 ... n = 4".
- 4 PASS: comparison table is split by 데이터1, 데이터2 (30행 제외) and 데이터2 (전체).
- 5 PASS: "+0.0232 [0.0069, 0.0395]".
- 6 PASS: "−0.0027 (95% CI −0.0143–0.0089, p_holm = 0.596)로 차이가 확인되지 않았다".
- 7 PASS: "+0.0349 [0.0247, 0.0451]" without the crash; −0.1035 with it, "결론이 완전히 뒤집힌다".
- 8 PASS: n, mean ± SD and 95% CI per group; CI and Holm p per comparison.
- 9 PASS: "11.85 ms → 30.24 ms (데이터1), 12.00 ms → 31.24 ms (데이터2)", about 2.6×.
- 10 PASS: "기준모델 | 17 | 0.7930 | 0.7517" and "17에폭 이후 검증정확도가 계속 떨어진다".
- 11 FAIL: Checked (1) +0.0232 [0.0069, 0.0395]: correct. (2) +0.0349 [0.0247, 0.0451]: correct. (3) 제안B 데이터2 latency 31.24 ± 0.47: correct. (4) epoch-30 0.7517 ± 0.0029: correct. (5) "모든 방법의 정확도가 데이터1보다 약 0.04 낮다": WRONG, 제안A is 0.064 lower.
- 12 PASS: 5 PNGs; axes labelled (방법/정확도, 지연시간 (ms), 에폭/검증 정확도); footers say "error bars: 95% CI" and "band: 95% CI".
- 13 PASS: Korean renders; legends sit outside the axes or in empty corners; no overlaps or clipping seen.
- 14 PASS: no bar charts. Fig1 excludes the crash and says so in the title; fig2 is a box plot that shows the crash as a point, titled "실패 런 포함", with no mean plotted.

## R03 (14/14)
- 1 PASS: "30행(제안B / 데이터2 / 시드4)의 정확도가 0.1021 ... Grubbs 검정에서도 이상치로 플래그".
- 2 PASS: separate tables for 데이터2 with the failed run "포함" and "제외".
- 3 PASS: "8행(제안A / 데이터1 / 시드2)의 정확도가 비어 있다 ... n=4".
- 4 PASS: separate "데이터1" and "데이터2" sections with their own tables.
- 5 PASS: "제안A − 기준모델 | +0.0232 [0.0069, 0.0395]".
- 6 PASS: "제안A는 데이터2에서 기준모델과 뚜렷한 차이가 없다 (차이 −0.0027, CI가 0을 포함)".
- 7 PASS: "+0.0349 [0.0247, 0.0451]"; with the crash "−0.1035 ... 아무 결론도 낼 수 없다".
- 8 PASS: n, SD and 95% CI per group; CI and Holm p per comparison.
- 9 PASS: "11.85 → 30.24 ms(2.55배) ... 12.00 → 31.24 ms(2.60배)".
- 10 PASS: "기준모델이 에폭 17(0.7930)에서 정점을 찍은 뒤 에폭 30(0.7517)까지 떨어진다".
- 11 PASS: Checked (1) +0.0232, p_holm 0.026: correct. (2) with crash −0.1035 [−0.4880, 0.2809]: correct. (3) 2.60× (12.00→31.24): correct. (4) epoch-30 diff +0.0805 [0.0743, 0.0866]: correct. (5) "CI 폭이 0.77": correct (0.7689).
- 12 PASS: 4 PNGs, all axes labelled; footers and captions give error bars "95% CI" and bands "95% CI".
- 13 PASS: Korean renders; legends sit outside the axes or in empty corners; no overlaps.
- 14 PASS: no bar charts (caption explains the dot-plot choice: "막대그래프는 0부터 시작해야 해서"). Fig1 excludes the crash and says so; fig2 box plot shows it as a point.

## R04 (14/14)
- 1 PASS: "30행 (제안B / 데이터2 / 시드4)의 정확도 0.1021은 Grubbs 검정(α=0.01)에서 이상치로 판정".
- 2 PASS: table "실패 run 포함 (n=5) ... / 실패 run 제외 (n=4)" and "본문 수치는 실패 run을 제외한 기준".
- 3 PASS: "8행 (제안A / 데이터1 / 시드2)의 정확도가 비어 있다 ... n=4".
- 4 PASS: "통합하지 않고 데이터셋별로 따로 분석했다"; tables per dataset.
- 5 PASS: "+0.0232 (95% CI 0.0069–0.0395, p_holm = 0.026, n=4 vs 5)".
- 6 PASS: "데이터2에서는 −0.0027 ... 차이가 확인되지 않았다".
- 7 PASS: "+0.0349 [0.0247, 0.0451]" without the crash; −0.1035 with it.
- 8 PASS: n, mean ± SD and CI per group; CI, Holm p and d per comparison.
- 9 PASS: "+18.39 ms (11.85 → 30.24 ms) ... +19.24 ms (12.00 → 31.24 ms)", "2.5배 이상".
- 10 PASS: "0.7930 (에폭 17) | 0.7517 | −0.0413"; "기준모델이 에폭 17 이후 하락".
- 11 PASS: Checked (1) +0.0349 [0.0247, 0.0451]: correct. (2) with crash 0.6560 ± 0.3097: correct. (3) latency +18.39 [16.68, 20.10]: correct. (4) peak-to-peak +0.0281 / +0.0449: correct. (5) "0.69 떨어져": correct (0.7882−0.1021 = 0.686).
- 12 PASS: 5 PNGs, all axes labelled; captions give "오차막대는 95% CI" and "음영은 95% CI", and footers repeat them.
- 13 PASS: Korean renders; no overlapping or clipped labels; the legends in fig4 and fig5 sit over empty space.
- 14 PASS: no bar charts (caption explains the dot-plot choice). Fig1 excludes the crash and says so; fig2 box plot shows it as a point with no mean.

## R05 (12/14)
- 1 PASS: "제안B · 데이터2 · 시드4 | 0.1021 ... 0.1021은 통계적 변동이 아니라 고장이다".
- 2 PASS: "학습 실패로 보고 제외 (n=4)", with a sensitivity table (제외 +3.49%p vs 포함 −10.35%p).
- 3 PASS: "제안A · 데이터1 · 시드2 | 정확도 칸이 비어 있음 ... 해당 런 제외 (n=4)".
- 4 PASS: §3 and §4 tables are per dataset; "방법 간 비교는 데이터셋 안에서만 해야 한다".
- 5 PASS: "데이터1 | 제안A | +2.32%p | [+0.69, +3.95]".
- 6 PASS: "데이터2 | 제안A | −0.27%p | [−1.43, +0.89] | ... | 차이 없음".
- 7 PASS: "+3.49%p [+2.47, +4.51]"; with the crash −10.35%p and "정반대 결론".
- 8 PASS: n, SD and 95% CI per group; CI, t (df) and Holm p per comparison.
- 9 PASS: "30.24ms 2.55배 (+18.39ms) ... 31.24ms 2.60배 (+19.24ms)".
- 10 PASS: "기준모델만 에폭 17 부근에서 꺾여 3.5%p 하락" and "마지막 에폭 값(0.752)"; fig3 is annotated "최고 0.793 (에폭 17) → 최종 0.752".
- 11 FAIL: Checked (1) +2.32%p, Holm p 0.0256: correct. (2) robust z ≈ 53: correct (53.3). (3) Mann-Whitney p for 제안A on 데이터2 = 0.690: correct. (4) "데이터2는 모든 방법에서 데이터1보다 3~4%p 낮다": WRONG, 제안A is 6.43%p lower. (5) "최고치 95% 도달 에폭" 기준모델 9.0: WRONG for the stated definition; per-seed 95%-of-max gives a mean of 10.7 (제안B 14.0, not 13.7). The values match 95% of the last-5-epoch mean instead.
- 12 PASS: 4 PNGs; axes labelled (정확도, 기준모델 대비 정확도 차이 (95% CI, Welch), 에폭/검증 정확도, 추론 지연시간 ms); subtitles say "가로선 = 95% CI", "± 1 표준편차" and "세로 막대 = 정확도 95% CI".
- 13 FAIL: in fig4 the labels "제안A 데이터1" and "제안B 데이터1" are drawn on top of their vertical CI bars, hiding the upper CI ends (zoomed).
- 14 PASS: no bar charts. Fig1 subtitle lists the crash as excluded; the plotted 제안B/데이터2 means (0.7944, +3.49%p) exclude it.

## R06 (13/14)
- 1 PASS: "2-1. 제안B / 데이터2 / 시드4 = 정확도 0.1021 (실패 런으로 판단)".
- 2 PASS: table "원자료 그대로 0.6560 ... -0.1035 / 실패 런 제외 (n=4) 0.7944 ... +0.0346"; the main analysis says it excludes the run.
- 3 PASS: "2-2. 제안A / 데이터1 / 시드2 = 정확도 결측 ... n=4".
- 4 PASS: §3-1 table gives each comparison per dataset.
- 5 PASS: paired +0.0198 [-0.0047, +0.0442], stated as paired with pairwise deletion. Recomputed: baseline on seeds 1,3,4,5 = 0.8013, so 0.8211−0.8013 = 0.0198, which is valid under that method.
- 6 PASS: "데이터2 | 제안A | ... -0.0027 | [-0.0111, +0.0057] | 0.424"; "데이터2 -0.3%p(효과 없음)".
- 7 PASS: paired +0.0346 [+0.0174, +0.0519] without the crash (correct for pairing); −0.1035 with it, and "결론이 정반대로 뒤집힙니다".
- 8 PASS: n, SD, 95% CI, p and dz per comparison.
- 9 PASS: "30.24 ms (2.55배) ... 31.24 ms (2.60배)" vs 11.85/12.00 ms.
- 10 PASS: "기준모델만 17에폭에서 정점(0.793)을 찍고 30에폭에서 0.752까지 떨어집니다(-0.041)".
- 11 PASS: Checked (1) paired +0.0198, p 0.082, dz 1.29: correct. (2) paired +0.0346 [+0.0174, +0.0519], p 0.008: correct. (3) IQR lower fence 0.6655: correct (Tukey fence over all 29 recorded accuracies). (4) "4~6%p 어렵습니다": correct (3.8/6.4/4.5%p). (5) minimum Wilcoxon p 0.0625 (n=5) and 0.125 (n=4): correct.
- 12 PASS: 4 PNGs; axes labelled (정확도, 기준모델 대비 정확도 차이/시드, 평균 추론 지연시간/평균 정확도, 에폭/검증 정확도); titles say "평균 ± 95% 신뢰구간" and "평균 ± 1 표준편차".
- 13 FAIL: in fig3 the labels "기준모델/데이터2" and "제안A/데이터2" overlap each other and the 제안A marker. In fig4 the curves cross the annotation "최고 0.793 (ep17)" (zoomed).
- 14 PASS: fig2 is a difference bar chart with bars from a zero baseline. Its × marks the missing and failed runs rather than using the crash. Fig1 notes the crash as excluded ("축 범위 밖, 집계에서 제외").
