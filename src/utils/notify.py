import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.exceptions import EmailError
from src.globals import get_config, get_logger
from src.globals.constants.config import (
    CHAIN_NAME_FIELD,
    EMAIL_RECEIVERS_FIELD,
    EMAIL_SENDER_FIELD,
    EMAIL_SMTP_PORT_FIELD,
    EMAIL_SMTP_SERVER_FIELD,
    LOGGER_DIR_FIELD,
    MAIN_DIR_FIELD,
)


def send_email(
    subject: str,
    body: str,
    attachments: list[tuple[str, str]] | None = None,
    dont_notify_devs: bool = False,
) -> None:
    """Sends an email to the provided developer address,
    as well as admin when allowed and applicable.

    Args:
        subject (str): The header for the mail
        body (str): Contents of th mail
        attachments (list[tuple[str, str]], optional): Defaults to None, in which case
        the log file will be provided as an attachment.
        attachments (list[tuple[str, str]], optional): Defaults to None, in which case
        will rely on --dont-notify-devs flag, to inform geodefi developers on crashes.

    Raises:
        EmailError:  when failed to send an email
    """

    # if dont_notify_devs is None:  # TODO:(later) we should ask or smt
    #     dont_notify_devs = dont_notify_devs

    msg: MIMEMultipart = MIMEMultipart()
    msg["From"] = get_config(field=EMAIL_SENDER_FIELD)
    msg["To"] = ",".join(get_config(field=EMAIL_RECEIVERS_FIELD))
    msg["Subject"] = f"[🧠 Geoscope]: {subject}"
    if not dont_notify_devs:
        body += (
            "\n\nGeodefi team is also notified of this error. "
            "You can use '--dont-notify-devs' flag to prevent this."
        )
        msg["Cc"] = "notifications@geode.fi"

    msg.attach(MIMEText(body, "plain"))

    if not attachments:
        main_dir: str = get_config(field=MAIN_DIR_FIELD)
        log_dir: str = get_config(field=LOGGER_DIR_FIELD)
        path: str = os.path.join(main_dir, log_dir, get_config(field=CHAIN_NAME_FIELD))
        attachments = [(path, "log.txt")]

    try:
        if attachments:
            for file_path, file_name in attachments:
                with open(file_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {file_name}")
                msg.attach(part)

    # pylint: disable-next=broad-exception-caught
    except Exception as e:
        get_logger().error(f"Failed to attach file {file_path}: {e}. Will try to send without it.")

    try:
        server = smtplib.SMTP(
            host=get_config(field=EMAIL_SMTP_SERVER_FIELD),
            port=get_config(field=EMAIL_SMTP_PORT_FIELD),
        )
        server.starttls()
        email_password = os.getenv("GEOSCOPE_EMAIL_PASSWORD")
        if email_password is None:
            raise EmailError("Email Password is not provided")
        server.login(get_config(field=EMAIL_SENDER_FIELD), email_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        get_logger().error("Failed to send email.")
        get_logger().error(str(e))
        raise EmailError("Failed to send an email") from e
