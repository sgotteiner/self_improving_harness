---
name: sr-lines-next-session
description: "Where the work stands (2026-10-11 end) - read the WHERE WE STAND block first: hybrid 4h ride (+9,141%, 61% won, unlevered) found, not built; 26 commits on develop unpushed"
metadata:
  node_type: memory
  type: project
  modified: 2026-10-11T19:43:54.290Z
  originSessionId: e117ceda-b2c9-4a17-9d14-a9b8f6377a8c
---

> Superseded for the CURRENT state by docs/DEVELOPMENT_METHODOLOGY.md §8 (2026-10-12). Kept as history.

## WHERE WE STOOD (end of 2026-10-11)
- develop at 6f3b982, 26 commits NOT pushed (push never confirmed - ask once).
- App (scripts/sr_playground.py, :8765): Trades card has 2 strategies - ride4h (DEFAULT: 4h internal-structure ride,
  his room rule, 244 trades, 30% won, +3,943%) and breakout (line breakout, 16 trades, 62.5%, +1,033%). Card: summary
  like his first dashboard, trade audit with each trade's 4h candles, risk/potential/best/got, "ideal moves (hindsight)"
  = the best 100 trades layer + score.
- FOUND, NOT BUILT (waiting his yes): the HYBRID = ride4h entries, held while the corrected daily trend is up, ride
  exits otherwise (stop 1 ATR under the internal low, lock 0.75R->+0.25R, turn sells from 2 ATR): BTC 90 trades, 61%
  won, +9,141%, DD -58%, c1 +2,590% c2 +244%. Confirmed on ETH (4h +3,048% vs hold +720%). Stocks: nothing beats B&H.
  Research scripts in session 6ca443a8 scratchpad (better.py, hybrid_markets.py, stop_test.py, ride_exact.py).
- His standing rules this session: no leverage, no shorts, real wins only (> +0.5%), no new data/markets unless he asks,
  trades must be explainable, research in scripts + ONE restart at the end, read every trade before reporting.
- HIS VERDICT at the end (2026-10-11): "we didnt pass buy and hold for stocks that went up and in general a lot is
  missing and another session is needed for debugging trying to understand mistakes and rules and research the
  internet and try to improve and i think it will be a lot more than one session". So the hybrid is NOT the finish
  line. The next sessions are a multi-session program: (1) debugging - audit our TA against cases every trader would
  mark (that is how the flipped-support and noise-target errors were found; more are likely); (2) understand our
  mistakes and our rules - why each strategy loses where it loses; (3) research the internet properly (methods, not
  just strategy names) and try them; (4) improve - with beating buy and hold on stocks that went up (Google, S&P) as
  an open, unsolved goal next to BTC.

2026-10-08/09: from tuning lines by eye to a backtested strategy. Committed and pushed: develop at
8a9c670 (2026-10-09) - check `git status` first for anything after it.

The design he set (all in docs/GEOMETRY_DEFINITIONS.md, why in DESIGN_DECISIONS_DIARY.md):
- Lines come ONLY from the frozen zigzag ("simple rule lines are based on zigzag"); a level needs 2+
  zigzag points; lines change only when the zigzag makes a point. One line source for page, events,
  strategy (business_logic_services/screen_lines.py, setup_history.py - disk cache, VERSION bump on rule change).
- The trend = his counted rule (2 higher highs AND 2 higher lows, not same height; "before that its
  noise"); its line starts where it began, over its own dots; a close beyond it is a breakout, not the
  end (zigzag_trend.py). Direction has ONE source - he rejected a second algorithm.
- Strength is part of every component (zigzag_strength.py); every line/trade card explains itself.
- Strategy (trade_view.py): breakout->retest of a zigzag line (no breakouts in a down trend) + higher
  low in an up trend; no target, stop rides the zigzag's higher lows. 30 trades, PF 2.40, +231%
  (2018-2022 PF 3.14, 2023-2026 PF 1.30); buy & hold +978%.

He works in rounds: "improve and backtest ... you can read all the trades yourself and after a run you
can ask me for changes" - don't ask at every trade. But never invent lines: when his rule is unclear,
measure against his drawings and ASK (six trend-line rules failed before his "a trend ends by its dots").

FIRST next round - his words: "our trades are fucking lost most of the time". 22 of 30 trades lose
(avg -6.6%, out in a median 8 days); the whole result is 3 winners (+54%, +72%, +102%) - without them
-38% compounded. A strategy that only works because of 3 trades is not an edge.
Open: breakout->retest entry loses (7 trades); 2023-2026 barely positive; counted trend opposite to him
at 2023-08-11 and 2026-09-04; 2022 line runs through the March high he calls noise; retest definition.

Round 2026-10-09 (measured, nothing changed in the repo, waiting on his answer): 14/22 losers never
reached +1R; after 18/22 stop-outs price kept falling (the stop is mostly right). His counted trend
read "up" at ALL 30 entries, incl. Sep 2022 (55-60% under the high) and 3 buys at the Dec 2024 top.
Variants (scratch only): higher-low only, stop 1.5% wider, buy on close above last peak - every one
is still -33%..-47% without its top 3. Asked him: is the trend reading at those dates right, and is
"rests on few trades" acceptable for a ride-the-trend exit or does he want a different exit.

2026-10-10 his verdict: "we dont have good lines we dont have nothing ... they dont look at the real
trend" + "we dont work with percentages we work with shapes and structures" (1.5% / 7% / even 0.45 of
the move are percentages - rejected). Measured 2022: the page HAD his 48k down trend (48,190 03-28 ->
40,024, 06-03..08-12), then pipe bounces flipped the count to "up" 08-17 (line 17,622 -> 18,511 on the
pipe floor); same in 04-08..05-27. 16 of 44 weeks "up" in 2022. Proposed (awaiting his yes + a sketch
of the pipe at 2022-09-16): dots inside a shape are touches of its walls, not steps; HH/HL count only
outside the shape. Strategy rounds paused until the trend is right (his 10-08 condition: "fine lines").
Then he: "are they stupid or you didnt follow them?" (the research). Answer: not followed - every source
reads structure at DEGREES (Dow primary/secondary, LuxAlgo/SMC swing vs internal, recursive zigzag); the
page reads ONE small degree = LuxAlgo's internal. Measured (scratch luxalgo_structure.py): swing (50 bars)
DOWN from 2022-05-09 through the whole pipe to 2023-03-17 (close 27,395 > 25,211 Aug top); internal UP on
2022-09-16, CHoCH up on 09-09 (our buy day). Swing lags: still "up" at 2022-03-04 where he drew a huge
down trend. Proposed: his counted rule at the swing degree, internal degree for entries; degree defined
without % (bars, or peaks-of-peaks). His call: "follow them correctly ... pick one and do it".
BUILT 2026-10-10: LuxAlgo SMC structure (modules/shapes/smc_structure.py, swing 50 / internal 5),
the one trend source (business_logic_services/structure_trend.py), page marks + checkboxes + top-bar
trend + cards (structure_view.py, ui/js/sr_playground/structure_marks.js). Counted rule removed
(zigzag_trend.py deleted). 7/9 of his up/down dates (was 5/9); strategy now 32 trades PF 1.96 +130%.
Next: his look; strategy rounds wait; levels still use 7% / 1.5% (percentages he rejected).
Server log now: scratchpad of session dff60293 (server_out.log).
2026-10-10 later: every card = fixed fields then "comments" (his line fields: total_strength_score,
start_dot, end_dot, touches_bounce_off, touches_breaks, size, duration, degree, comments; events, trades,
structure marks the same - line_card.py, trade_card.py, event_story.fields, card_fields.js). Open trades
are shown as of the date on screen (trade_card.as_of) - they had leaked their future. Then: "degree" =
the line's ANGLE on the chart (line_angle.js, zoom-dependent, %/day beside it), "degree_type" = swing /
zigzag 7%, "current_state" = his active / broken / flipped (+ being tested now); breaks counted by closes
beyond the touch zone. Commits 2bd37e7, ac1b37b, 0ba34d7 on develop, NOT pushed.
Cold start fixed (db14c9d): frozen_points rows decided once - trades 139 s -> 2.5 s, identical on 3,106 days.
STRENGTH SCORE STUDY (2026-10-10, his "make the score as best as possible"): 1,756 line tests 2018-2026
(scripts/line_strength_study.py, uncommitted with line_strength.py): no card parameter predicts holding
stably - every one flips direction between 2018-20 / 2021-22 / 2023+ (swing_sum 0.42/0.35/0.56; "with the
swing trend" held 48v65, 65v75, 85v64). Only stable: support (price above) holds more: 60v51, 71v66, 83v68.
A fitted score tested 0.52 on 2023+. -> no score built (diary). Then his order: "80% win rate ... just
follow them correctly ... dont come back with 25%". BUILT the dip in the trend (strategies/dip_in_trend.py,
dip_trades.py, simulate_bounce): weekly+daily swing+internal up, 3 lower closes, stop 2nd rung, out at first
close > SMA5 in profit after fees. 48 trades 90% won PF 2.46 (+133%); 25/88%/2.32 and 23/91%/2.75 by period.
Weak: small wins, wide stops, far under B&H; the dip rule's neighbours lose in 2018-22. Trades card default,
old "ride" selectable. Research scripts in session dff60293 scratchpad (research.py, r1-r23).
Then his correction: "luxalgo ... way better than buy and hold ... profit is more important obviously".
DEFAULT NOW (f259f57): ride the internal structure (strategies/structure_trend.py, trend_trades.py): long
while LuxAlgo's daily internal (5-bar) trend is up, in/out on the close of its turns: +1,286% vs B&H +978%,
DD -59% vs -77%, 41 trades, 44% won (avg +37.6% / -9.7%). Wins by losing less in bear years; lags in 2023-24.
Trades card shows profit + DD vs B&H for every strategy. Every early exit tried for win rate cost most of the
profit. Open: win rate of the profit system; lag in strong bulls. Commits through f259f57 NOT pushed.
Then "do better ... 43000% in cycle 2 (a lookahead bug) ... better winrate and profit" + "no shorts".
PROFIT LOCK (781a836): after a close 0.6R up, resting stop at buy+fees -> +2,242% vs B&H +978%, 63% won
(8 scratches), DD -59%. Chosen on cycle 1 (project cycles: config/constants.py, cycle 2 = 2021-11-10 on).
Tested & dropped: shorts (all L/S worse), 1h timing (fees), slow direction filters on 4h, picking degrees by
result (no degree wins both cycles). 4h + lock made +3,841% (59% won) but the page is daily. NOT pushed.
"yes add the hourly" -> f165045: 4h bars from btc_1h_extended (intraday_bars.py), trend4h = Trades card
DEFAULT (+3,841%, DD -56%, 246 trades, 59%); card shows per-cycle vs hold; cycle 2 OOS daily better (card,
equity split at 2021-11-10: daily +154% vs 4h +83%, hold +21%; by trade entry dates it was +199% vs +93% -
always quote the card's numbers, never mix the two). Push never confirmed - his "yes add the hourly" did not clearly cover it; ask once more.
2026-10-11 his rule: "you can do percentages relative to the timeframe maybe but not absolute percentages
because 7% hourly and daily are very different". FIRST JOB next session (diary entry written, code not):
zigzag 7% -> 1.7x ATR, touch zone 1.5% (6 copies: SAME_LINE_PCT, TOUCH_PCT x2, SAME_PCT x2, ON_LEVEL_PCT)
+ stars 1.4% -> 0.36x ATR (median ATR daily 4.15%, 4h 1.54%, 1h 0.74%). Recommended ATR as of the date
(option B), then re-check his reviewed dates. Fees stay %.
DONE 2026-10-11 (5b71019, his "do what you think is best ... tell me if it improved"): timeframe_ruler.py,
option B, zigzag floor 1.7x + touch 0.36x ATR(14) of each day, on the page's zigzag mode + all trades. Dip
+133% -> +181% (94% won, DD -32 -> -23%, both cycles up); old ride +130 -> +113%; structure rides unchanged.
His 13 drawn/judged lines on screen 4 -> 2, but 09-04 now shows 81.5k (his 80,277 / 79,500) instead of
67k/58k. Not converted yet: owner/concepts modes, events' concept lines, %/day slope tolerances. Pre-existing
failing test: test_zigzag_strength held_days (key never existed). Measure script: session 6ca443a8 scratchpad.
2026-10-11 his "consider 0.1 as a loss" / "only real trades ... 80% winrate of real trades and 5000%+": a win =
> +0.5% (trade_simulator.REAL_WIN_PCT, card counts it; 4h ride is 30% real). Built profit4h (d09f19b,
strategies/profit_ride.py, a Trades card choice): 4h turn up, stop 2nd rung, lock 0.5R->0.25R, turn sells only
2 ATR up: 90 trades 81% real, +3,589%, DD -61%, c2 +203%. ~11,000 variants: 80% real + >3,841% NOT found
(best +3,812%); leverage 1.2x -> +5,591% offered, not done. He asked "why dont i see it in the app" - he
expects results in the app, not only in research tables.
2026-10-11 his "the bug is the lines algorithm" (2025-12-03 read UP in the 126k->92k fall) + "fix the trends and
lines. we can't do strategies ... without good lines" -> 349f6b8: structure_fall.py (a close taking back 2/3 of the
rise turns it down; 2/3 of the fall back undoes it), swing 32 bars, trend line over INTERNAL highs from the swing
extreme, frozen once a close is 3 ATR beyond. His 10 dated trends 10/10 (was 7). Lines vs his 5 drawn: 2 within 3%,
3 within 5% (2022-03-04 +6% skips his Feb high choice, 2023-04-21 -12%). Strategy rounds wait for his look at
the lines. Then "i dont understand this trade it didnt bounce off anything, didnt break anything" + "its on
you to improve and backtest" -> 5f48f20: DEFAULT = "breakout" (strategies/line_breakout.py): daily close over a
page line (from an open under it), trend not down, stop 1 ATR under, real-profit exit; broken line drawn on the
trade. 19 trades, 89% real, +427%, DD -34%, c1 +134 c2 +125. Next: more trades without losing the reason
(it is under B&H in cycle 1). c683fdb: "your trades are not based on lines not explainable and i dont want
them" -> ALL other strategies removed (rides, profit ride, dip, old ride); the app has only "breakout". Every
future strategy must trade a line on his page and say which. 5b0de8a after "1% trades? really bro? ... analyze
your work for once ... dont restart the server a million times use the logs and show me only when its done":
the lock (0.5R) took all 9 small wins on the line's retest -> stop 0.5 ATR under line, lock to the line's top at
1R, turn sells 4 ATR up: 16 trades, wins +13..+94%, +1,033% (hold +978%), DD -37%, c2 +167%. ALWAYS read every
trade (best vs kept) before reporting; research in scripts, ONE restart at the end. 1244183 "i want the 4000
one just make it better ... if it uses hourly too i wanna see it": ride4h back as DEFAULT (strategies/structure_ride.py,
ride4h_cards.py), trade audit draws each trade's 4h candles (/api/trade_bars). Couldn't make it better on cycle 1
(diary has the variants). Strategies on the card: ride4h, breakout. eef7a1d: every trade shows risk /
potential (next zigzag level above, known day before) / best / got. Finding: ride4h median trade +5.6% room, best
+3.4%, kept +0.1% - its exit gives everything back; no better stop exists (worst trade -8.8%). ca37f3b his
"potential less than the average move of 14 candles i dont want" = ATR(14) room rule on ride4h only: +3,943%,
DD -56%, c2 +101% (breakout: it hurt, +1,033 -> +379, not applied). 4dd9200 HIS GOAL: the best 100 trades with
hindsight (DP, daily closes, fees) = "ideal moves (hindsight)" layer + every strategy scored (caught / taken / noise).
ride4h 82/100 takes 7%, 79 noise; breakout 16/100 takes 36%, 0 noise. His priority now (2026-10-11): WIN RATE and
QUALITY per trade over BTC profit - "theres a million things to trade". Patterns: bull flag best (9 trades 89%,
+46% avg); H&S / cup found once each (zigzag too coarse) - next: fix detectors (ATR, finer zigzag / 4h), measure
against the 100. Edit scripts with nested quotes: Write a .py file, never a Bash heredoc (eval wrapper breaks them).

Ops: the page server runs detached (PowerShell Start-Process, log in the session scratchpad) and warms
itself at start (WARM lines ~12s, trades ~100s). Logs: VIEW, EVENTS, TRADES, CARD (what he clicked).
Real-browser checks: headless Chrome via http://localhost:8765 with --disable-extensions (the
127.0.0.1 URL is redirected by a web filter). Bash heredocs with ${...} break - use Edit/Write
([[bash-heredoc-backticks]]).
