# -*- coding: utf-8 -*-

# # import asyncio
# # EMAIL RELATED
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from email.mime.base import MIMEBase
# from email import encoders
# import smtplib
# from smtplib import SMTPResponseException

# # TELEGRAM RELATED
# import token
# from telegram import Bot
# from telegram.error import BadRequest

# # GEODE RELATED
# from geode.utils.wrappers import multipleAttempt

# # TODO_unrelated: CYPHER to fix config.json


# class GalileoException(Exception):
#     """Something is wrong with SMTP server or Telegram API"""

#     # TODO_unrelated move this to exceptions.py file
#     pass


# # import from .env
# PASSWORD = "aaaa"
# BOT_TOKEN = "6741622673:AAGGU4NTH9ZeE0JhlE4auSHJHQ_TdtD9GvM"


# # dict (str->dict) later give key
# @multipleAttempt
# def send_email_by_smtp(email_config: dict):
#     """
#     Sends an email using SMTP with the given configuration.

#     :param email_config: A dictionary containing email configuration details.
#         It should have the keys: 'emails', 'sender_email', 'subject', 'body', 'filename'.
#     :type email_config: dict

#     :return: None
#     """

#     # Extracting information from the email configuration
#     try:
#         targets = email_config["emails"]
#         sender = email_config["sender_email"]
#         subject = email_config["subject"]
#         body = email_config["body"]
#         filename = email_config["filename"]
#     except KeyError as e:
#         print("Missing value in config.json")
#         raise e

#     # Iterating over the list of target email addresses
#     for to_address in targets:
#         # Creating a MIMEMultipart object to represent the email
#         msg = MIMEMultipart()
#         msg["From"] = sender
#         msg["To"] = to_address
#         msg["Subject"] = subject

#         # Adding the body of the email as plain text
#         msg.attach(MIMEText(body, "plain"))

#         # Adding an attachment (if specified in the configuration)
#         if filename != "":
#             attachment = open(filename, "rb")
#             part = MIMEBase("application", "octet-stream")
#             part.set_payload((attachment).read())
#             encoders.encode_base64(part)
#             part.add_header("Content-Disposition", f"attachment; filename={filename}")
#             msg.attach(part)

#         # Converting the email object to a string
#         text = msg.as_string()

#         # Establishing a connection to the SMTP server (Gmail in this case)
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()

#         try:
#             # Attempting to login to the SMTP server using the provided credentials
#             # Consider passing PASSWORD as a parameter or from a secure source
#             server.login(sender, PASSWORD)
#         except:
#             # Handling incorrect credentials
#             GalileoException(f"GALILEO: Incorrect Credentials.")
#             break  # Consider using a more specific exception or logging the error

#         try:
#             # Attempting to send the email
#             server.sendmail(sender, to_address, text)
#         except SMTPResponseException as e:
#             # Handling SMTP response exceptions
#             raise GalileoException(f"GALILEO: {e} sendmail error.")


# @multipleAttempt
# def send_telegram_message(telegram_config: dict):
#     """
#     Sends a message to a user on Telegram using the provided configuration.

#     :param telegram_config: A dictionary containing Telegram configuration details.
#         It should have the keys: 'user_id' and 'body'.
#     :type telegram_config: dict

#     :return: None
#     """

#     # Initialize the Telegram bot with the specified token
#     # Ensure that BOT_TOKEN is defined or passed as a parameter
#     bot = Bot(token=BOT_TOKEN)

#     # Extracting information from the Telegram configuration
#     user_id = telegram_config["user_id"]
#     body = telegram_config["body"]

#     try:
#         # Attempting to send a message to the user on Telegram
#         bot.send_message(chat_id=user_id, text=body)
#     except BadRequest as e:
#         # Handling Telegram BadRequest exceptions
#         raise GalileoException(f"GALILEO: {e} telegram error.")
