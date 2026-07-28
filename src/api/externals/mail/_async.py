import os
import pathlib
import logging
from email.message import EmailMessage, Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from pydantic import validate_call, EmailStr, NameEmail, SecretStr, AnyHttpUrl
from jinja2 import Environment, FileSystemLoader

from api.config import config

logger = logging.getLogger(__name__)

_current_file_dir = pathlib.Path(__file__).resolve().parent
_TEMPLATES_DIR = os.path.join(_current_file_dir, "templates")


@validate_call(config={"arbitrary_types_allowed": True})
async def async_send(
    host: str,
    port: int,
    username: EmailStr | str,
    password: SecretStr,
    start_tls: bool,
    from_addr: NameEmail,
    to_addrs: EmailStr | list[EmailStr],
    subject: str,
    message: MIMEMultipart | EmailMessage | Message | str,
    cc_emails: EmailStr | list[EmailStr] | None = None,
    bcc_emails: EmailStr | list[EmailStr] | None = None,
) -> None:
    """Send an mail using the SMTP server.

    Args:
        host       (str                             , required): SMTP server host.
        port       (int                             , required): SMTP server port.
        username   (EmailStr | str                  , required): SMTP server user email.
        password   (SecretStr                       , required): SMTP server password.
        start_tls  (bool                            , required): Use STARTTLS.
        from_addr  (NameEmail                       , required): Sender email address.
        to_addrs   (EmailStr | list[EmailStr]       , required): Recipient email address(es).
        subject    (str                             , required): Subject of the mail.
        message    (MIMEMultipart | EmailMessage |
                                       Message | str, required): Mail message.
        cc_emails  (EmailStr | list[EmailStr] | None, optional): CC email address(es). Defaults to None.
        bcc_emails (EmailStr | list[EmailStr] | None, optional): BCC email address(es). Defaults to None.

    Raises:
        ValueError: If port and starttls are not matching.
        Exception : If sending the mail fails.
    """

    if ((not start_tls) and (port != 465)) or (start_tls and (port != 587)):
        raise ValueError(
            "Port 465 is for SMTP over SSL and port 587 is for SMTP with STARTTLS (TLS)."
        )

    if isinstance(message, str):
        _mime_text = MIMEText(message, "plain")
        message = MIMEMultipart()
        message.attach(_mime_text)

    message["Subject"] = subject
    message["From"] = str(from_addr)

    _all_recipients = []
    if isinstance(to_addrs, str):
        message["To"] = to_addrs
        _all_recipients.append(to_addrs)
    elif isinstance(to_addrs, list):
        message["To"] = ", ".join(to_addrs)
        _all_recipients.extend(to_addrs)

    if cc_emails:
        if isinstance(cc_emails, str):
            message["Cc"] = cc_emails
            _all_recipients.append(cc_emails)
        elif isinstance(to_addrs, list):
            message["Cc"] = ", ".join(cc_emails)
            _all_recipients.extend(cc_emails)

    if bcc_emails:
        if isinstance(bcc_emails, str):
            _all_recipients.append(bcc_emails)
        if isinstance(to_addrs, list):
            _all_recipients.extend(bcc_emails)

    _use_tls = True
    if start_tls:
        _use_tls = False

    logger.debug(f"Sending mail to {_all_recipients} with subject '{subject}'...")
    try:
        await aiosmtplib.send(
            message,
            sender=str(from_addr),
            recipients=_all_recipients,
            hostname=host,
            port=port,
            username=username,
            password=password.get_secret_value(),
            use_tls=_use_tls,
            start_tls=start_tls,
        )

        logger.debug(
            f"Successfully sent mail to {_all_recipients} with subject '{subject}'."
        )
    except Exception:
        logger.debug(
            f"Failed to send mail to {_all_recipients} with subject '{subject}'!"
        )
        raise

    return


@validate_call
async def async_send_verify(
    email: EmailStr,
    verify_url: AnyHttpUrl | SecretStr,
    template_path: str = os.path.join(_TEMPLATES_DIR, "signup-verification.html"),
) -> None:
    """Send a verification mail to the user's email address.

    Args:
        email         (EmailStr              , required): Email address to send the mail.
        verify_url    (AnyHttpUrl | SecretStr, required): URL to verify the email address.
        template_path (str                   , optional): Path to the template file.
                                                            Defaults to `templates_dir` + "signup-verification.html".

    Raises:
        FileNotFoundError: If mail template file not found.
        Exception        : If sending the mail fails.
    """

    _verify_url = str(verify_url)
    if isinstance(verify_url, SecretStr):
        _verify_url = verify_url.get_secret_value()

    _txt_msg = f"""
        Welcome to example.com, {email}!

        Please confirm your email address to activate your example.com account.
        Click the link below to continue the activation process:

        URL: {_verify_url}

        If you did not sign up for this account, you can ignore this email and this account will be deleted later.
        """

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Mail template file not found: {template_path}!")

    _template_dir = os.path.dirname(template_path)
    _template_fname = os.path.basename(template_path)

    _jinja_env = Environment(
        loader=FileSystemLoader(searchpath=_template_dir, followlinks=True),
        autoescape=True,
    )
    _mail_template = _jinja_env.get_template(name=_template_fname)
    _html_msg = _mail_template.render(email=email, verify_url=_verify_url)

    _message = MIMEMultipart("alternative")
    _message.attach(MIMEText(_txt_msg, "plain", "utf-8"))
    _message.attach(MIMEText(_html_msg, "html", "utf-8"))

    await async_send(
        host=config.mail.host,
        port=config.mail.port,
        username=config.mail.username,
        password=config.mail.password,
        start_tls=config.mail.starttls,
        from_addr=config.mail.from_addr,
        to_addrs=email,
        subject="Verify your email [example.com]",
        message=_message,
    )

    return


@validate_call
async def async_send_reset_password(
    email: EmailStr,
    reset_password_url: AnyHttpUrl | SecretStr,
    template_path: str = os.path.join(_TEMPLATES_DIR, "reset-password.html"),
) -> None:
    """Send a password reset mail to the user's email address.

    Args:
        email              (EmailStr              , required): Email address to send the mail.
        reset_password_url (AnyHttpUrl | SecretStr, required): URL to reset the password.
        template_path      (str                   , optional): Path to the template file.
                                                                Defaults to `templates_dir` + "reset-password.html".

    Raises:
        FileNotFoundError: If mail template file not found.
        Exception        : If sending the mail fails.
    """

    _reset_password_url = str(reset_password_url)
    if isinstance(reset_password_url, SecretStr):
        _reset_password_url = reset_password_url.get_secret_value()

    _txt_msg = f"""
        Hello, {email}!

        We have received a request to reset your account password.
        Please click the link below to complete the password reset process:

        URL: {_reset_password_url}

        If you need additional assistance, or you did not make this request, please contact to support@example.com.
        """

    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Mail template file not found: {template_path}!")

    _template_dir = os.path.dirname(template_path)
    _template_fname = os.path.basename(template_path)

    _jinja_env = Environment(
        loader=FileSystemLoader(searchpath=_template_dir, followlinks=True),
        autoescape=True,
    )
    _mail_template = _jinja_env.get_template(name=_template_fname)
    _html_msg = _mail_template.render(
        email=email, reset_password_url=_reset_password_url
    )

    _message = MIMEMultipart("alternative")
    _message.attach(MIMEText(_txt_msg, "plain", "utf-8"))
    _message.attach(MIMEText(_html_msg, "html", "utf-8"))

    await async_send(
        host=config.mail.host,
        port=config.mail.port,
        username=config.mail.username,
        password=config.mail.password,
        start_tls=config.mail.starttls,
        from_addr=config.mail.from_addr,
        to_addrs=email,
        subject="Reset your password [example.com]",
        message=_message,
    )

    return


__all__ = [
    "async_send",
    "async_send_verify",
    "async_send_reset_password",
]
