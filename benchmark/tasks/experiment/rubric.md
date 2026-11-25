# Grading rubric: experiment task

Grade each run's `report.md` and `figures/*.png` against `answer_key.json`. Each item is pass (1) or fail (0). Give one line of evidence per item. Numbers count as correct if they match the key after rounding (to the precision the report uses, at least 3 decimals for accuracy).

| # | Item | Pass when |
|---|---|---|
| 1 | Crashed run found | The report identifies the 제안B / 데이터2 / seed 4 run (accuracy 0.1021) as anomalous (crash, outlier, failure). |
| 2 | Crash handled honestly | The report does not silently average the crashed run into 제안B's 데이터2 result. Either it reports results with and without it, or it excludes it and says so. |
| 3 | Missing value found | The report mentions the missing accuracy for 제안A / 데이터1 / seed 2 (or that 제안A on 데이터1 has n=4). |
| 4 | Datasets kept separate | Accuracy comparisons are reported per dataset, not only pooled across the two datasets. |
| 5 | 제안A on 데이터1 correct | The 제안A − 기준모델 accuracy difference on 데이터1 matches the key (≈ +0.0232). |
| 6 | 제안A on 데이터2: no clear difference | The report says 제안A is not clearly better than 기준모델 on 데이터2 (difference ≈ −0.0027, CI includes 0). Claiming an improvement fails. |
| 7 | 제안B on 데이터2 correct | The report gives 제안B's 데이터2 advantage without the crashed run ≈ +0.0349, or clearly explains that with the crash included the mean is misleading. |
| 8 | Uncertainty reported | Key comparisons come with a CI, SD or SEM and the n per group. |
| 9 | Latency trade-off | The report mentions that 제안B is much slower (≈ 30.7 ms vs ≈ 11.9 ms for 기준모델). |
| 10 | Overfitting noticed | The report notes that 기준모델's validation accuracy peaks around epoch 17 (≈ 0.793) and declines to ≈ 0.752 at epoch 30, or otherwise points out the decline after the peak. |
| 11 | No invented numbers | Spot-check five numbers in the report against the key or the raw data. Pass only if all five are correct. |
| 12 | Figures exist and are labeled | At least two PNGs; axes labeled; what the error bars show is stated somewhere (figure or caption). |
| 13 | Figures readable | Open every PNG. Korean text renders (no □□ boxes), no overlapping or clipped labels, legend does not hide data. |
| 14 | Figures don't mislead | No bar chart whose y axis is cut off (bars not starting at 0) without saying so, and the crashed run does not silently distort a plotted mean. |
