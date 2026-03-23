import logging
import asyncio
import httpx
import sqlite3
import os
import time
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============ 사용자 설정 구간 ==============
#https://www.d2tz.info/online 사이트 가입 후 API 입력
API_TOKEN = ''
TELEGRAM_TOKEN = ''
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'd2r_user_storage.db')
# ============================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (chat_id TEXT PRIMARY KEY, targets TEXT)')
    conn.commit()
    return conn

db_conn = init_db()

# 🗺️ 매핑 테이블
ZONE_KOR_MAP = {
    #ACT1
    "Blood_Moor": "핏빛 황무지", "Den_of_Evil": "악의 소굴", "Cold_Plains": "차디찬 평야", "Cave": "동굴",
    "Burial_Grounds": "매장지", "Crypt": "묘실", "Mausoleum": "영묘", "Stony_Field": "바위 벌판",
    "Dark_Wood": "어둠숲", "Underground_Passage": "지하 통로", "Black_Marsh": "검은 습지", "Hole": "구렁",
    "Forgotten_Tower": "잊힌 탑(백작)", "Jail": "감옥", "Catacombs": "카타콤(안다)", "Tristram": "트리스트럼",
    "Cathedral":"대성당", "Inner_Cloister":"내부 회랑", "Barracks" : "병영",
    "Moo_Moo_Farm": "카우방", "Secret Cow Level": "카우방",

    #ACT2
    "Lut_Gholein_Sewers": "ACT2 하수도", "Dry_Hills": "메마른 언덕", "Halls_of_the_Dead": "죽음의 홀", "Far_Oasis": "먼 오아시스",
    "Lost_City": "잊힌 도시", "Valley_of_Snakes": "뱀의 골짜기", "Claw_Viper_Temple": "발톱 독사 사원",
    "Ancient_Tunnels": "고대 토굴",
    "Maggot_Lair": "구더기 굴", "Arcane_Sanctuary": "비전의 성역", "Harem": "하렘", "Palace_Cellar": "궁전 지하",
    "Tal_Rashas_Tomb": "탈 라샤의 무덤", "Tal_Rashas_Chamber": "탈 라샤의 방(듀리얼)",

    #ACT3
    "Spider_Forest": "거미 숲", "Arachnid_Lair": "독거미 둥지", "Spider_Cavern": "거미 동굴", "Great_Marsh": "거대 습지",
    "Flayer_Jungle": "약탈자 밀림", "Flayer_Dungeon": "약탈자 소굴", "Lower_Kurast": "하부 쿠라스트", "Swampy_Pit": "습한 구덩이",
    "Kurast_Bazaar": "쿠라스트 시장", "Kurast_Causeway": "쿠라스트 둑길", "Kurast_Sewers": "하수도",
    "Ruined_Temple": "버려진 유적", "Disused_Fane": "버려진 성소", "Forgotten_Reliquary": "잊힌 유적",
    "Forgotten_Temple": "잊힌 사원", "Travincal": "트라빈칼", "Durance_of_Hate": "증오의 억류지(메피)",

    #ACT4
    "Outer_Steppes": "지옥 외곽 평원", "Plains_of_Despair": "절망의 평원", "City_of_the_Damned": "저주받은 자들의 도시",
    "River_of_Flame": "불길의 강", "Chaos_Sanctuary": "혼돈의 성역(디아)", 
    
    #ACT5
    "Bloody_Foothills": "핏빛 언덕",
    "Frigid_Highlands": "혹한의 고산지", "Arreat_Plateau": "아리앗 고원", "Pit_of_Acheron": "아케론의 구덩이",
    "Crystal_Passage": "수정 동굴",
    "Frozen_River": "얼어붙은 강", "Glacial_Trail": "빙하의 길", "Drifter_Cavern": "부랑자의 동굴",
    "Nihlathaks_Temple": "니흘라탁의 사원", "Halls_of_Vaught": "전당(나락)", "Ancients_Way": "고대인의 길",
    "Halls_of_Anguish": "고뇌의 전당", "Halls_of_Pain":"고통의 전당",
    "Icy_Cellar": "얼음 지하실", "Worldstone_Keep": "세계석 성채", "Throne_of_Destruction": "파괴의 왕좌", "Worldstone_Chamber": "세계석 보관실(바알)"
}

ACT_DATA = {
    "ACT I": ["핏빛 황무지, 악의 소굴", "차디찬 평야, 동굴", "매장지, 묘실, 영묘", "바위 벌판, 트리스트럼", "어둠숲, 지하 통로", "검은 습지, 구렁, 잊힌 탑(백작)", "감옥, 병영", "카타콤(안다)", "카우방"],
    "ACT II": ["하수도", "메마른 언덕, 죽음의 홀", "먼 오아시스, 구더기 굴", "잊힌 도시, 뱀의 골짜기", "비전의 성역, 하렘, 궁전 지하", "탈 라샤의 무덤(듀리얼)"],
    "ACT III": ["거미 숲, 거미 동굴", "거대 습지", "약탈자 밀림, 소굴, 습한 구덩이", "쿠라스트 시장, 둑길, 하부", "트라빈칼", "증오의 억류지(메피)"],
    "ACT IV": ["평원 외곽, 절망의 평원", "불길의 강, 저주받은 도시", "혼돈의 성역(디아)"],
    "ACT V": ["핏빛 언덕, 혹한의 고산지", "아리앗 고원, 아케론의 구덩이", "수정 동굴, 얼어붙은 강", "빙하의 길, 부랑자의 동굴", "고대인의 길, 얼음 지하실", "니흘라탁의 사원(나락)", "세계석 성채, 파괴의 왕좌(바알)"]
}

# --- 헬퍼 함수 ---
def get_user_targets(chat_id):
    c = db_conn.cursor()
    c.execute("SELECT targets FROM users WHERE chat_id=?", (str(chat_id),))
    row = c.fetchone()
    return [t for t in row[0].split('|') if t] if row and row[0] else []

def save_user_targets(chat_id, targets_list):
    c = db_conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (chat_id, targets) VALUES (?, ?)", (str(chat_id), '|'.join(targets_list)))
    db_conn.commit()

async def get_combined_msg():
    url = f"https://api.d2tz.info/public/tz?token={API_TOKEN}"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10)
            data = res.json()
            data.sort(key=lambda x: x['time'])
            now_ts = time.time()
            curr, nxt = None, None
            for i, e in enumerate(data):
                if e['time'] <= now_ts < e.get('end_time', e['time'] + 3600):
                    curr = e
                    if i + 1 < len(data): nxt = data[i+1]
                    break
            if not curr: curr = data[0]
            def kor(names): return ", ".join([ZONE_KOR_MAP.get(n, n.replace('_', ' ')) for n in names])
            def fmt(ts): return datetime.fromtimestamp(ts).strftime('%Y. %m. %d. %p %I:%M:%S').replace('AM', '오전').replace('PM', '오후')
            msg = f"🚨 <b>현재 공포의 영역</b> 🚨\n<b>{kor(curr.get('zone_name'))}</b>\n시작: {fmt(curr['time'])}\n\n"
            if nxt:
                msg += f"🔮 <b>다음 공포의 영역</b> 🔮\n<b>{kor(nxt.get('zone_name'))}</b>\n시작: {fmt(nxt['time'])}"
            return msg, curr['time']
        except: return "❌ 정보를 가져오지 못했습니다.", None

# --- 하단 고정 메뉴 ---
def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("➕ 알림추가"), KeyboardButton("➖ 알림삭제")],
        [KeyboardButton("📜 알림목록"), KeyboardButton("🎸 현재 공포영역")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- 핸들러 함수들 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "<b>🎮 디아2 알리미 가동!</b>\n하단 버튼을 이용하세요.",
        reply_markup=main_menu_keyboard()
    )

async def current_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg, _ = await get_combined_msg()
    await update.message.reply_html(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ 알림추가":
        await addzone_menu(update, context)
    elif text == "➖ 알림삭제":
        await delzone_menu(update, context)
    elif text == "📜 알림목록":
        await myzone(update, context)
    elif text == "🎸 현재 공포영역":
        await current_zone(update, context)

def get_act_keyboard():
    keyboard = [[InlineKeyboardButton(act, callback_data=f"addact_{act}")] for act in ACT_DATA.keys()]
    return InlineKeyboardMarkup(keyboard)

async def addzone_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚩 추가할 지역의 ACT를 선택하세요.", reply_markup=get_act_keyboard())

async def delzone_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    targets = get_user_targets(update.effective_chat.id)
    if not targets:
        await update.message.reply_text("📋 삭제할 지역이 없습니다.")
        return
    keyboard = [[InlineKeyboardButton(f"❌ {loc}", callback_data=f"del_{loc}")] for loc in targets]
    await update.message.reply_text("🗑️ 삭제할 지역을 선택하세요.", reply_markup=InlineKeyboardMarkup(keyboard))

async def myzone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    targets = get_user_targets(update.effective_chat.id)
    await update.message.reply_html(f"📋 <b>내 알림 리스트:</b>\n\n" + ("\n".join(targets) if targets else "등록된 지역 없음"))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data.startswith("addact_"):
        act = query.data.replace("addact_", "")
        keyboard = [[InlineKeyboardButton(loc, callback_data=f"save_{loc}")] for loc in ACT_DATA[act]]
        keyboard.append([InlineKeyboardButton("⬅️ 뒤로가기", callback_data="back_to_acts")])
        await query.edit_message_text(f"📍 <b>{act}</b> 지역 선택", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif query.data == "back_to_acts":
        await query.edit_message_text("🚩 추가할 지역의 ACT를 선택하세요.", reply_markup=get_act_keyboard())

    elif query.data.startswith("save_"):
        loc = query.data.replace("save_", "")
        targets = get_user_targets(chat_id)
        if loc not in targets:
            targets.append(loc)
            save_user_targets(chat_id, targets)
            await query.message.reply_html(f"✅ <b>{loc}</b> 등록 완료!")

    elif query.data.startswith("del_"):
        loc = query.data.replace("del_", "")
        targets = get_user_targets(chat_id)
        if loc in targets:
            targets.remove(loc)
            save_user_targets(chat_id, targets)
            await query.message.reply_html(f"🗑️ <b>{loc}</b> 삭제 완료!")

async def auto_alarm(context: ContextTypes.DEFAULT_TYPE):
    msg, start_time = await get_combined_msg()
    last_time = context.job.data if context.job.data else 0
    if start_time and start_time > last_time:
        context.job.data = start_time
        c = db_conn.cursor()
        c.execute("SELECT chat_id, targets FROM users")
        for cid, t_str in c.fetchall():
            targets = t_str.split('|')
            if any(t.split(',')[0].strip() in msg for t in targets if t):
                try: await context.bot.send_message(chat_id=cid, text=msg, parse_mode='HTML')
                except: pass

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("current_zone", current_zone))
    app.add_handler(CommandHandler("addzone", addzone_menu))
    app.add_handler(CommandHandler("delzone", delzone_menu))
    app.add_handler(CommandHandler("myzone", myzone))
    
    # 버튼 텍스트 핸들러
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    app.job_queue.run_repeating(auto_alarm, interval=60, first=10)
    
    print("🤖 봇 가동 시작...")
    app.run_polling()

if __name__ == "__main__":
    main()
