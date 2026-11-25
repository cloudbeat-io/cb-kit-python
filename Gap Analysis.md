# TODO - Feature Roadmap

Feature gap analysis compared to Allure Report and ReportPortal.

_Updated 2026-11-25 against branch `feature/console-capture` (not released; PyPI is still at 1.2.1)._
Items marked _server_ are now done by CloudBeat itself (Test Health), not by the kit; what the kit still has
to send for them is listed under "Data CloudBeat needs from the kit".

## Test Organization & Metadata

- [ ] `@cb.epic`, `@cb.feature`, `@cb.story` — BDD-style hierarchy for grouping tests beyond suites. Slice results by business domain (e.g., "Security" > "Login" > "SSO Login").
- [ ] `@cb.severity` / `@cb.priority` — Mark tests as BLOCKER, CRITICAL, NORMAL, MINOR, TRIVIAL. Enable filtering reports by impact level.
- [ ] `@cb.tag` / `@cb.label` — Arbitrary key-value labels for flexible grouping/filtering (e.g., `@cb.tag("smoke")`, `@cb.tag("regression")`). pytest markers need no kit support: CloudBeat reads them as tags from the code when the project syncs and runs a tag with `-m <tag>`. Only markers added at run time would be missing.
- [ ] `@cb.owner` — Assign test ownership to a team member.
- [ ] `@cb.link` / `@cb.issue` / `@cb.tms_link` — Associate tests with Jira tickets, bug IDs, or test management system entries.

## Rich Content & Attachments

- [ ] `cb.attach(data, name, type)` — Attach arbitrary content to the current step/case: HTML, JSON, text, images, videos. Only screenshots are supported, only via the Selenium listener. `TestableResultBase.attachments` exists but nothing fills it and `json_util` does not write it.
- [ ] `@cb.description` / `@cb.title` — Override the test display name and add rich (markdown/HTML) descriptions. Currently only `name` and `description` from docstrings.
- [x] Step parameters display — `@cb.step` stores the arguments passed to the step (`StepResult.arguments`, `[{name, value}]` as `repr`, without `self` / `cls` / `*args` / `**kwargs`) and writes them to the results JSON. _`feature/console-capture`_

## Test Lifecycle

- [x] Retry tracking — with `pytest-rerunfailures` the result keeps the last attempt only, with `reRunCount` = the number of re-runs, so a test that passed on a re-run is reported as passed (before, the first failure stuck and it was reported failed) and CloudBeat counts it as flaky. _`feature/console-capture`_
- [x] Flaky test detection — _server_: Test Health marks tests Flaky / Broken / Regressed from their run history.
- [x] Test history & trends — _server_: Test Health shows the last 10–50 runs, durations and trends per test; Optimize finds fixed sleeps, long timeouts and slow tests.
- [x] Defect classification — _server_: every failure gets a Failure Reason (Flaky, Environment, Defect, Test Data, Broken, To Investigate) from rules, run history and AI, and people can change it. The kit's `FailureResult.type` (SELENIUM_ERROR, ASSERT_ERROR, GENERAL_ERROR) is one of the inputs.

## Environment & Configuration

- [ ] Environment info in report — `test_attributes` holds hostname/OS only; browser version and base URL are not reported. _Partly done:_ each test's context now has `automation` (engine Appium/Selenium, platform, platform version, automation name, browser, device) from the wrapped driver. _`feature/console-capture`_
- [x] Categories/custom failure classifiers — _server_: built-in and custom classification rules (exception name, text or regex, per framework and engine) in Test Health.

## Fixtures & Hooks

- [ ] Fixture-level reporting — Report each fixture (setup/teardown) as a visible, expandable section with its own steps and attachments. The `hooks` list exists but only captures "setup"/"teardown" as flat names.

## Logging & Console Output

- [x] Log capture per step — `CbLoggingHandler` routes Python `logging` records to the running step, else the test case (`logs`: message, level, time, src); levels mapped (warning → warn, error/critical → error). _`feature/console-capture`_
- [x] stdout/stderr capture — `print()` / stdout (info) and stderr (error) go into the same logs. While pytest captures output (the default; CloudBeat runs without `-s`) the kit takes pytest's captured output of each phase; with `-s` `CbStreamWrapper` tees the streams instead. _`feature/console-capture`_

## Real-time & Live Reporting

- [x] Live test status — test case start/end is sent to CloudBeat as tests run (`RuntimeApiV2`). Full results (steps, logs, screenshots) are still sent as one JSON file at session end, which is how CloudBeat takes them.
- [x] Launch/run management — _server_: CloudBeat keeps runs with their history, filters and per-test health.

## Parallel Execution

- [ ] Parallel/distributed test reporting — Aggregate results from multiple `pytest-xdist` workers. `ThreadContext` handles threads but `xdist` uses separate processes.

## Mobile (Appium)

- [ ] Appium support — `CbSeleniumWrapper` wraps any Selenium-compatible driver, so Appium drivers get steps and screenshots, and the engine stamp recognises them (driver class or `platformName` / `automationName` capabilities). Not done: Appium exceptions (`appium.common.exceptions`) are reported as GENERAL_ERROR instead of a driver error type, and there is no Appium-specific documentation or test.

## Data CloudBeat needs from the kit (Test Health)

- [x] Automation engine per test — context `automation` (see above), so engine rules (Appium vs Selenium) apply to pytest projects. _`feature/console-capture`_
- [x] Re-run count per test — `reRunCount`, so "passed on retry" counts as flaky. _`feature/console-capture`_ (The .NET kit sends it too; the Java kit does not yet.)
- [ ] Failure location — file and line of the failing test code (the .NET kit sends it), for grouping errors and for code-level optimization suggestions.

## Known limitations

- The reporter keeps the last wrapped driver per thread, so in a mixed suite a later test that uses no driver (e.g. an API test) still gets the previous driver's `automation` stamp.
- `cb-kit-pytest/tests/test_plugin.py` is a leftover template (`hello` fixture, `--name` option, `cbx.pw.hello`): 3 of its tests fail on the committed code too. Replace it with real plugin tests.
- `cb-kit-playwright` is a stub (`hello(world)`).
