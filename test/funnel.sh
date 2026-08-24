#!/usr/bin/env bash
# ファネル計測の一発チェック。3セッション分を投げて /dash の数字が合うか見る。
# 前提: 空のローカルD1 に waitlist テーブルだけある状態で走らせる(件数を絶対値で検査するため)。
#   wrangler d1 execute DB -c wrangler.toml --local --persist-to state --command "CREATE TABLE ..."
#   wrangler pages dev . --d1 DB=ainori-waitlist --persist-to state --port $PORT
set -u
B=http://127.0.0.1:${PORT:-8788}
K=ainori-7f3c9a21e4
fail=0
ok(){ echo "  ok   $1"; }
ng(){ echo "  NG   $1"; fail=1; }
chk(){ [ "$2" = "$3" ] && ok "$1 = $2" || ng "$1: expected $3, got $2"; }

ev(){ curl -s -X POST $B/api/ev -H 'content-type: application/json' -d "{\"n\":\"$2\",\"sid\":\"$1\",\"src\":\"$3\"}"; }

echo "== 投入 =="
# s1: 最後まで行って登録
for n in view sec:yoru sec:tana sec:tsukai sec:anshin sec:register form_focus lead; do ev s1 "$n" 'ref:t.co' >/dev/null; done
# s2: 第参で離脱
for n in view sec:yoru sec:tana sec:tsukai; do ev s2 "$n" 'ref:t.co' >/dev/null; done
# s3: ファーストビューで離脱、流入元なし
ev s3 view '' >/dev/null
# s1 の view を再送 → PRIMARY KEY(sid,name) で二重計上されないこと
ev s1 view 'ref:t.co' >/dev/null
echo "  投入完了"

echo "== バリデーション =="
chk "不正なイベント名は拒否" "$(curl -s -o /dev/null -w '%{http_code}' -X POST $B/api/ev -H 'content-type: application/json' -d '{"n":"drop table","sid":"x"}')" "400"
chk "sid なしは拒否"        "$(curl -s -o /dev/null -w '%{http_code}' -X POST $B/api/ev -H 'content-type: application/json' -d '{"n":"view"}')" "400"
chk "GET は拒否"            "$(curl -s -o /dev/null -w '%{http_code}' $B/api/ev)" "405"

echo "== ダッシュボード =="
chk "鍵なしは404"   "$(curl -s -o /dev/null -w '%{http_code}' $B/dash)" "404"
chk "鍵違いは404"   "$(curl -s -o /dev/null -w '%{http_code}' "$B/dash?k=wrong")" "404"
H=$(curl -s "$B/dash?k=$K&d=30")
chk "鍵ありは200"   "$(curl -s -o /dev/null -w '%{http_code}' "$B/dash?k=$K")" "200"

# KPI: LP到達3 / フォーム到達1 / 登録1 / CVR 33.3%
num(){ echo "$H" | tr '>' '\n' | grep -A0 -m"$2" -oP '(?<=^)'"$1" | tail -1; }
chk "LP到達"        "$(echo "$H" | grep -oP '<b>\K[0-9.%]+' | sed -n 1p)" "3"
chk "フォーム到達"  "$(echo "$H" | grep -oP '<b>\K[0-9.%]+' | sed -n 2p)" "1"
# 3枚目のKPIは waitlist 由来の「実ユーザー登録」。テストは waitlist を空にして走らせる
chk "実ユーザー登録" "$(echo "$H" | grep -oP '<b>\K[0-9.%]+' | sed -n 3p)" "0"
# CVR は計測イベント同士(登録完了 1 ÷ LP到達 3)。DB由来の数を混ぜると100%を超える
chk "CVR"           "$(echo "$H" | grep -oP '<b>\K[0-9.%]+' | sed -n 4p)" "33.3%"
chk "段:登録完了"   "$(echo "$H" | grep -A4 '>登録完了<' | grep -oP 'class="num">\K[0-9]+' | head -1)" "1"
echo "$H" | grep -oP '[0-9]+(\.[0-9]+)?(?=%)' | awk '$1>100' | grep -q . && ng "100%超えの数字がある" || ok "100%超えの数字なし"

# 段: 壱=2人(s1,s2) / 肆=1人 / 「参で2人が肆へ落ちた」= 50%離脱が bad 表示
chk "壱 覚えのある夜 の人数" "$(echo "$H" | grep -A4 '壱 覚えのある夜' | grep -oP 'class="num">\K[0-9]+' | head -1)" "2"
chk "肆 安心設計 の人数"     "$(echo "$H" | grep -A4 '肆 安心設計' | grep -oP 'class="num">\K[0-9]+' | head -1)" "1"

# 流入元別: ref:t.co が2人 / (direct) が1人
echo "$H" | grep -q 'ref:t.co' && ok "流入元 ref:t.co が出ている" || ng "流入元 ref:t.co が無い"
echo "$H" | grep -q '(direct)' && ok "流入元 (direct) が出ている" || ng "流入元 (direct) が無い"

# 静的アセットの素通しが生きているか(これを壊すとサイト全体が落ちる)
chk "/ が200"        "$(curl -s -o /dev/null -w '%{http_code}' $B/)" "200"
chk "/privacy が200" "$(curl -s -o /dev/null -w '%{http_code}' $B/privacy)" "200"
curl -s $B/ | grep -q "__ev" && ok "LPに計測が入っている" || ng "LPに計測が無い"

# 登録完了はサーバー側が撃つ(クライアントの sendBeacon 頼みだと JS切り/離脱で落ちる)。
# /api/ev を一度も叩かずに /api/register だけ投げて、段が増えることを見る。
# @example.com なので waitlist 側の「実ユーザー」には数えられない = 上の絶対値検査を汚さない
echo "== 登録完了のサーバー側計測 =="
curl -s -X POST $B/api/register -H 'content-type: application/json'   -d '{"sid":"s4","email":"t4@example.com","area":"渋谷|ref:t.co"}' >/dev/null
H2=$(curl -s "$B/dash?k=$K&d=30")
chk "段:登録完了(s1 + s4)" "$(echo "$H2" | grep -A4 '>登録完了<' | grep -oP 'class="num">\K[0-9]+' | head -1)" "2"
chk "sid なしの登録は段を増やさない" "$(curl -s -o /dev/null -w '%{http_code}' -X POST $B/api/register -H 'content-type: application/json' -d '{"email":"t5@example.com"}')" "200"

echo
[ $fail -eq 0 ] && echo "PASS" || echo "FAIL"
exit $fail
