# -*- coding: utf-8 -*-

import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.common import AttributeDict
from src.exceptions import EmailError
from src.globals import get_config, get_logger


def send_email(
    subject: str, body: str, attachments: list[tuple[str, str]] = [], dont_notify_devs=None
):
    """Sends an email to the provided developer address,
    as well as admin when allowed and applicable.

    Args:
        subject (_type_): The header for the mail
        body (_type_): Contents of th mail
        attachments (list[tuple[str, str]], optional): Defaults to None, in which case
        the log file will be provided as an attachment.
        attachments (list[tuple[str, str]], optional): Defaults to None, in which case
        will rely on --dont-notify-devs flag, to inform geodefi developers on crashes.

    Raises:
        e: _description_
        e: _description_
    """
    config: AttributeDict = get_config()

    if config.email is None:
        return

    if dont_notify_devs is None:
        dont_notify_devs = config.email.dont_notify_devs

    msg: MIMEMultipart = MIMEMultipart()
    msg["From"] = config.email.sender
    msg["To"] = ",".join(config.email.receivers)
    msg["Subject"] = f"[🧠 Geonius]: {subject}"
    if not dont_notify_devs:
        body += (
            "\n\nGeodefi team is also notified of this error. "
            "You can use '--dont-notify-devs' flag to prevent this."
        )
        msg["Cc"] = "notifications@geode.fi"

    msg.attach(MIMEText(body, "plain"))

    if not attachments and not config.logger.no_file:
        main_dir: str = config.dir
        log_dir: str = config.logger.dir
        path: str = os.path.join(main_dir, log_dir, "log")
        attachments: list[tuple[str, str]] = [(path, "log.txt")]

    try:
        for file_path, file_name in attachments:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {file_name}")
            msg.attach(part)
    except Exception as e:
        get_logger().error(f"Failed to attach file {file_path}: {e}. Will try to send without it.")

    try:
        server = smtplib.SMTP(config.email.smtp_server, config.email.smtp_port)
        server.starttls()
        server.login(config.email.sender, os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)
        server.quit()
    except Exception as e:
        get_logger().error(f"Failed to send email.")
        get_logger().error(str(e))
        raise EmailError(f"Failed to send an email") from e
