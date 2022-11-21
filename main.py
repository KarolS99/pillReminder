import os
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update  #upm package(python-telegram-bot)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, PicklePersistence  #upm package(python-telegram-bot)
from datetime import datetime as dt
import pytz

###############CONSTANTS##################
#STATES
MAIN_OPTION, REMINDER_OPTION, DELETE_OPTION, SELECT_TIME, SELECT_DAYS, SELECT_NAME, PROCEED_ADD, PROCEED_DELETION, PROCEED_TIMEZONE, SHOW, QUIT = range(
  11)
#DOMAINS and FORMATS
#days
TIMEZONES = ["europe", "pacific", "indian", "america", "asia", "australia"]
DAYS_DOMAIN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN", "ALL"]
DAY_STR_TO_NUM = {
  "MON": 0,
  "TUE": 1,
  "WED": 2,
  "THU": 3,
  "FRI": 4,
  "SAT": 5,
  "SUN": 6,
  "ALL": 7,
}
DAY_NUM_TO_STR = {
  0: "MON",
  1: "TUE",
  2: "WED",
  3: "THU",
  4: "FRI",
  5: "SAT",
  6: "SUN",
  7: "ALL",
}
#time
TIME_FORMAT = "%H:%M"

#fixed keyboards
MAIN_KEYBOARD = [["Pill reminders"], ["Prescription reminders"]]
REMINDER_KEYBOARD = [["Add reminder", "Delete reminder", "Show reminders"],
                      ["Done"]]
PRESCRIPTION_KEYBOARD = [[
  "Add prescription", "Delete prescription", "Show prescriptions"
], ["Done"]]

###############CONSTANTS##################


#flags for unsupported formats
name_fail = False
time_fail = False
day_fail = False

# Enable logging
import logging

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO)
logger = logging.getLogger(__name__)


#FUNCTIONS TO HANDLE JOBS
def alarm(context: CallbackContext) -> None:
  """Send the alarm message."""
  job = context.job
  context.bot.send_message(job.context,
                           text="It's " + job.name[9:] + " time!⏰")

def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
  """Remove job with given name. Returns whether job was removed."""
  current_jobs = context.job_queue.get_jobs_by_name(name)
  if not current_jobs:
    return False
  for job in current_jobs:
    job.schedule_removal()
  return True
  

#FUNCTIONS TO GATHER USER DATA
def retrieve_user_data(context,type):
  '''Returns a list of user reminders'''
  return [
    value for key, value in context.user_data.items() if type in key
  ]


#BOT OPERATIONS

#SHOW
def show_reminders(update: Update, context: CallbackContext) -> int:
  ''' Shows user's registrated timers for reminders'''
  reminders = retrieve_user_data(context, 'reminder')
  if len(reminders) > 0:
    reply_string = "\u23F0Those are your present reminders\u23F0\n\n"
    for reminder in reminders:
      days = [DAY_NUM_TO_STR[day] for day in reminder.get("days")]
      reply_string += "\U0001F48A " + reminder.get(
        "medicine") + "\n\U0001F553 " + reminder.get(
          "time") + "\n\U0001F5D3 " + ' '.join(days) + "\n\n"
    update.message.reply_text(reply_string)
  else:
    update.message.reply_text(
      "\n\n..wait, it looks like you have to setup a timer yet!")
  return REMINDER_OPTION
  
#DELETE
def delete(update: Update, context: CallbackContext) -> int:
  '''Cancel a saved reminder'''
  reminders = retrieve_user_data(context,'reminder')
  if len(reminders):
    reply_keyboard_row, reply_keyboard = [], []

    #create keyboard containing reminders
    for reminder in reminders:
      reply_keyboard_row.append(reminder.get("medicine"))
      if len(reply_keyboard_row) % 3 == 0:
        reply_keyboard.append(reply_keyboard_row)
        reply_keyboard_row = []
    if reply_keyboard_row:
      reply_keyboard.append(reply_keyboard_row)
    reply_keyboard.append(["Cancel"])
    markup = ReplyKeyboardMarkup(reply_keyboard,
                                 one_time_keyboard=True,
                                 input_field_placeholder="Reminder")

    update.message.reply_text("Which reminder do you want to delete?",
                              reply_markup=markup)
    return DELETE_OPTION
  else:
    markup = ReplyKeyboardMarkup(
      [["Add reminder", "Delete reminder", "Show reminders"], ["Done"]],
      one_time_keyboard=True,
      input_field_placeholder="Choice")
    update.message.reply_text(
      "If you have no reminders, how can you delete one?", reply_markup=markup)
    return REMINDER_OPTION

def after_delete(update: Update, context: CallbackContext) -> int:
  """Deletes reminder"""
  to_delete = update.message.text
  try:
    removed = remove_job_if_exists("reminder_" + to_delete, context)
    del context.user_data['reminder_' + to_delete]

    text = "Reminder was removed." if removed else "Couldn't remove reminder."
    markup = ReplyKeyboardMarkup([["Yes", "No"]],
                                 one_time_keyboard=True,
                                 input_field_placeholder="Continue?")
    update.message.reply_text(text +
                              "\nDo you need to delete any other reminder?",
                              reply_markup=markup)
    return PROCEED_DELETION
  except:
    update.message.reply_text("Your reminder doesn't exist :(")

#ADD
def add_name(update: Update, context: CallbackContext) -> int:
  '''Handles pill add'''
  global name_fail
  text = "Your name is not lower than 10 characters, try with another name (no special characters accepted)" if name_fail else "You are adding a pill reminder. Please, enter the name of the medication. It must be lower than 10 characters and contain no special character."
  update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
  name_fail = True
  return SELECT_NAME

def add_time(update: Update, context: CallbackContext) -> int:
  '''Handles time adding'''
  global time_fail, name_fail
  name_fail = False
  #save choosen med
  if time_fail:
    update.message.reply_text(
      "Time was not in the right format! Enter a valid time in HH:MM format (with a leading zero)"
    )
  else:
    context.user_data["temp_rem"] = {"medicine": update.message.text}
    update.message.reply_text(
      "Fine! Now, tell me what time do you take your medication? You should type time in HH:MM format)"
    )
  time_fail = True
  return SELECT_TIME


#HERE I should implement an inline keyboard 
#
#
def add_day(update: Update, context: CallbackContext) -> int:
  '''Handles day choice '''
  global day_fail, time_fail
  time_fail = False
  day = update.message.text.lstrip('❌')
  #if time is not saved, save it and initialize days list
  if context.user_data["temp_rem"].get("time") is None:
    context.user_data["temp_rem"].update({
      "time": update.message.text,
      "days": []
    })

  #add chosen day, if not chosen yet. Else, delete it
  if day in DAYS_DOMAIN:
    day_to_add = DAY_STR_TO_NUM[day]
    if day_to_add == 7:
      context.user_data["temp_rem"]["days"] = [0, 1, 2, 3, 4, 5, 6]
    elif day_to_add not in context.user_data["temp_rem"]["days"]:
      context.user_data["temp_rem"]["days"].append(day_to_add)
    else:
      context.user_data["temp_rem"]["days"].remove(day_to_add)
  else:
    day_fail = True

  #keyboard is built dinamically according to which elements are currently selected
  chosen_days = []
  for day in context.user_data["temp_rem"].get("days"):
    chosen_days.append(DAY_NUM_TO_STR[day])
  not_chosen_days = [day for day in DAYS_DOMAIN if day not in chosen_days]
  chosen_days = ['❌' + day for day in chosen_days]

  markup = ReplyKeyboardMarkup([not_chosen_days, chosen_days, ["That's all"]],
                               one_time_keyboard=True,
                               input_field_placeholder="Days")
  update.message.reply_text("Add days or remove them", reply_markup=markup)
  return SELECT_DAYS


def after_add(update: Update, context: CallbackContext) -> int:
  """Adds reminder definitely """
  global day_fail
  user_id = update.message.chat_id
  text = ""

  try:
    #reset global variable
    day_fail = False

    #remove old job if exists
    job_removed = remove_job_if_exists(
      "reminder_" + context.user_data["temp_rem"].get("medicine"), context)
    #server time is utc, client time is selected with /timezone
    timezone1 = pytz.timezone("UTC")
    timezone2 = pytz.timezone(context.user_data["region"] + '/' +
                              context.user_data["timezone"])

    #time_for_job is not enough cause pytz may give historical value,so I use today's date
    time_for_job = dt.strptime(context.user_data["temp_rem"].get("time"),
                               time_format)
    recent_time_for_job = dt.now().replace(hour=time_for_job.hour,
                                           minute=time_for_job.minute)

    #convert it from local timezone to utc
    recent_time_for_job = timezone2.localize(recent_time_for_job)
    converted_date = recent_time_for_job.astimezone(timezone1)
    utc_time_for_job = converted_date.time()

    days_to_run = tuple(context.user_data["temp_rem"].get("days"))
    #finally run the job
    context.job_queue.run_daily(alarm,
                                utc_time_for_job,
                                days_to_run,
                                context=user_id,
                                name="reminder_" +
                                context.user_data["temp_rem"].get("medicine"))

    text = "Reminder added! You will receive a message whenever you have to take your " + context.user_data[
      "temp_rem"].get("medicine") + "."
    if job_removed:
      text += "Old one was removed."
    update.message.reply_text(text)

    #cancel temp data
    context.user_data["reminder_" + context.user_data["temp_rem"].get(
      "medicine")] = context.user_data["temp_rem"]
    context.user_data["temp_rem"] = []

    markup = ReplyKeyboardMarkup([["Yes", "No"]],
                                 one_time_keyboard=True,
                                 input_field_placeholder="Choice?")
    update.message.reply_text("Do you need to add any other reminder?",
                              reply_markup=markup)

    return PROCEED_ADD

  except:
    update.message.reply_text(
      "Something went wrong and I couldn't add a reminder..",
      reply_markup=ReplyKeyboardMarkup(REMINDER_KEYBOARD,
                                       one_time_keyboard=True,
                                       input_field_placeholder="Choice?"))
    return REMINDER_OPTION

#MAIN CONV
def start(update: Update, context: CallbackContext) -> int:
  """Starts the conversation by showing a menu"""
  #check if timezone is already specified, else set default (UTC)
  try:
    timezone_text = "\nCurrent timezone: " + context.user_data[
      'region'] + "/" + context.user_data['timezone']
  except:
    timezone_text = "\nNo timezome selected: Europe/London (UTC/GMT) will be used, but you can change your timezone by using /timezone"
    context.user_data['region'], context.user_data[
      'timezone'] = "Europe", "London"

  
  markup = ReplyKeyboardMarkup(MAIN_KEYBOARD,
                               one_time_keyboard=True,
                               input_field_placeholder="Menu")
  update.message.reply_text(
    "Hello there! I can send you a message whenever you need to take a medication or renew your prescription.\U0001F468\U0001F3FB\u200D\u2695\uFE0F\n Choose an option below"
    + timezone_text,
    reply_markup=markup)

  return MAIN_OPTION


def ask_reminders_option(update: Update, context: CallbackContext) -> int:
  markup = ReplyKeyboardMarkup(REMINDER_KEYBOARD,
                               one_time_keyboard=True,
                               input_field_placeholder="Menu")
  update.message.reply_text("What do you want me to do?", reply_markup=markup)
  return REMINDER_OPTION

def quit(update: Update, context: CallbackContext) -> int:
  """Exit the conversation"""
  update.message.reply_text("Okay, see you soon!",
                            reply_markup=ReplyKeyboardRemove())
  return ConversationHandler.END


#TIMEZONE
def timezone_selection(update: Update, context: CallbackContext) -> int:
  '''Allows user to select a timezone'''

  common_timezones = pytz.common_timezones

  #build a keyboard with timezones in region
  if context.args:
    if context.args[0].lower() in TIMEZONES:
      try:
        context.user_data['region'] = context.args[0].lower().capitalize()
        #pytz looks into IANA databases for timezones in the selected region and put them as keyboard buttons
        reply_keyboard, reply_keyboard_row = [], []
        for timezone in common_timezones:
          if timezone.lower().startswith(context.args[0].lower()):
            reply_keyboard_row.append(timezone[len(context.args[0]) + 1:])
            if len(reply_keyboard_row) % 3 == 0:
              reply_keyboard.append(reply_keyboard_row)
              reply_keyboard_row = []
        #remainder
        reply_keyboard.append(reply_keyboard_row)

        reply_keyboard = ReplyKeyboardMarkup(reply_keyboard)
        update.message.reply_text("Pick a timezone",
                                  reply_markup=reply_keyboard)
        return PROCEED_TIMEZONE
      except:
        update.message.reply_text("Error in timezone selection")
    else:
      update.message.reply_text(
        "You should type one of the following with your command: Europe, Pacific, Indian, America, Asia, Australia"
      )
  else:
    update.message.reply_text(
      "Couldn't save timezone. Right use for the command is /timezone region\n"
    )
  return MAIN_OPTION

def timezone_pick(update: Update, context: CallbackContext) -> None:
  '''Handles user timezone choice method'''
  reply_keyboard = [["Add reminder", "Delete reminder", "Show reminders"],
                    ["Done"]]
  reply_keyboard = ReplyKeyboardMarkup(reply_keyboard,
                                       one_time_keyboard=True,
                                       input_field_placeholder="Choice?")
  try:
    context.user_data["timezone"] = update.message.text
    update.message.reply_text(
      "Timezone was correctly selected! Now all the timers will work according to your current timezone: "
      + context.user_data["region"] + "/" + context.user_data["timezone"],
      reply_markup=reply_keyboard)
  except:
    update.message.reply_text("Error in timezone selection",
                              reply_markup=reply_keyboard)
  return MAIN_OPTION



def main():
  persistence = PicklePersistence(filename="conversationbot")
  updater = Updater(os.getenv("TOKEN"), persistence=persistence)
  dispatcher = updater.dispatcher

  conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
      MAIN_OPTION: [
        MessageHandler(Filters.regex("^Pill reminders$"),
                       ask_reminders_option),
        MessageHandler(Filters.regex("^Prescription reminders$"),
                       ask_prescriptions_option),
        CommandHandler("timezone", timezone_selection),
      ],
      REMINDER_OPTION: [
        MessageHandler(Filters.regex("^Show reminders$"), show_reminders),
        MessageHandler(Filters.regex("^Add reminder$"), add_name),
        MessageHandler(Filters.regex("^Delete reminder$"), delete),
        CommandHandler("timezone", timezone_selection),
      ],
      DELETE_OPTION: [
        CommandHandler("quit", quit),
        MessageHandler(Filters.text & (~Filters.regex("^Cancel$")),
                       after_delete),
        MessageHandler(Filters.regex("^Cancel$"), ask_reminders_option),
      ],
      PROCEED_DELETION: [
        MessageHandler(Filters.regex("^Yes$"), delete),
        MessageHandler(Filters.regex("^No$"), ask_reminders_option),
      ],
      SELECT_NAME: [
        CommandHandler("quit", quit),
        MessageHandler(Filters.regex("^[a-zA-Z1-9]{0,10}$"), add_time),
        MessageHandler(Filters.text & (~Filters.regex("^[a-z && A-Z]{0,10}$")),
                       add_name),
      ],
      SELECT_TIME: [
        CommandHandler("quit", quit),
        MessageHandler(Filters.regex("^([0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$"),
                       add_day),
        MessageHandler(
          Filters.text &
          (~Filters.regex("^([0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$")), add_time),
      ],
      SELECT_DAYS: [
        CommandHandler("quit", quit),
        MessageHandler(Filters.regex("^(MON|TUE|WED|THU|FRI|SAT|SUN|ALL)$"),
                       add_day),
        MessageHandler(Filters.regex("^That\'s all"), after_add),
        MessageHandler(
          Filters.text &
          (~Filters.regex("^(MON|TUE|WED|THU|FRI|SAT|SUN|ALL)$")), add_day)
      ],
      PROCEED_ADD: [
        MessageHandler(Filters.regex("^Yes$"), add_name),
        MessageHandler(Filters.regex("^No$"), ask_reminders_option),
      ],
      PROCEED_TIMEZONE: [
        CommandHandler("quit", quit),
        MessageHandler(Filters.regex("^[a-zA-Z_//]{0,15}$"), timezone_pick),
        MessageHandler(Filters.text & (~Filters.regex("^[a-z && A-Z]{0,10}$")),
                       timezone_selection),
      ],
    },
    fallbacks=[
      CommandHandler("quit", quit),
      MessageHandler(Filters.regex("^Done$"), start)
    ],
    name="my_conversation",
    persistent=True,
  )

  dispatcher.add_handler(conv_handler)
  updater.start_polling()
  updater.idle()


if __name__ == '__main__':
  main()
