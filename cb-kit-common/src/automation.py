"""Describes the automation engine behind a WebDriver: Appium (mobile) or Selenium (browser).

Stored in each test result's context as "automation", so CloudBeat (Test Health) knows what a pytest project
actually drove and applies the matching rules. Never raises: a driver that cannot tell gives None.
"""


def describe_driver(driver):
    if driver is None:
        return None
    try:
        # EventFiringWebDriver -> the driver it wraps
        driver = getattr(driver, "wrapped_driver", None) or driver
        caps = getattr(driver, "capabilities", None)
        caps = caps if isinstance(caps, dict) else {}

        def text(name):
            value = caps.get(name)
            if value is None:
                return None
            value = str(value).strip()
            return value or None

        def cap(name):  # "platformName" or the W3C-prefixed "appium:platformName"
            return text(name) or text("appium:" + name)

        platform = cap("platformName")
        automation_name = cap("automationName")
        is_appium = _is_appium_type(type(driver)) or automation_name is not None \
            or (platform or "").lower() in ("ios", "android")

        info = {"engine": "appium" if is_appium else "selenium"}
        for key, value in (("platform", platform), ("automationName", automation_name),
                           ("browser", text("browserName")), ("device", cap("deviceName")),
                           ("platformVersion", cap("platformVersion"))):
            if value is not None:
                info[key] = value
        return info
    except Exception:
        return None


def _is_appium_type(cls):
    # appium.webdriver.webdriver.WebDriver and subclasses; the kit does not depend on the Appium client
    return any((c.__module__ or "").startswith("appium.") for c in getattr(cls, "__mro__", ()))
