"""
IP address utilities.

Provides functions for safely extracting client IP addresses from requests,
with protection against IP address spoofing via X-Forwarded-For header.
"""

import ipaddress

from starlette.requests import Request

from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.settings import app_settings


def is_trusted_proxy(ip_address_str: str) -> bool:
    """
    Check if an IP address belongs to a trusted proxy.

    Args:
        ip_address_str: IP address string to check.

    Returns:
        True if the IP is in the trusted proxy list, False otherwise.
    """
    if not app_settings.TRUSTED_PROXIES:
        return False

    try:
        ip_addr = ipaddress.ip_address(ip_address_str)

        for proxy in app_settings.TRUSTED_PROXIES:
            try:
                # Check if it's a network (CIDR notation)
                if "/" in proxy:
                    network = ipaddress.ip_network(proxy, strict=False)
                    if ip_addr in network:
                        return True
                # Check if it's a single IP
                elif ip_addr == ipaddress.ip_address(proxy):
                    return True
            except ValueError as ex:
                logger.warning(
                    f"Invalid proxy address in TRUSTED_PROXIES: {proxy} - {ex}"
                )
                continue

        return False

    except ValueError as ex:
        logger.warning(f"Invalid IP address: {ip_address_str} - {ex}")
        return False


def get_client_ip(request: Request) -> str:
    """
    Safely extract the client IP address from a request.

    Checks X-Forwarded-For header only if the request comes from a
    trusted proxy to prevent IP address spoofing.

    Args:
        request: The incoming HTTP request.

    Returns:
        The client IP address as a string.
    """
    # Get the immediate client IP (could be a proxy)
    client_host = request.client.host if request.client else "unknown"

    # Check if we have X-Forwarded-For header
    forwarded_for = request.headers.get("X-Forwarded-For")

    if forwarded_for and is_trusted_proxy(client_host):
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # The first IP is the original client
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug(
            f"Using X-Forwarded-For IP: {client_ip} "
            f"(proxied through {client_host})"
        )
        return client_ip

    # Either no X-Forwarded-For or not from trusted proxy
    if forwarded_for and not is_trusted_proxy(client_host):
        logger.warning(
            f"Ignoring X-Forwarded-For from untrusted source: {client_host}"
        )

    return client_host
