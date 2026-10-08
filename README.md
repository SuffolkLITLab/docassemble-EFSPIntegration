# docassemble-EFSPIntegration

[![PyPI version](https://badge.fury.io/py/docassemble.EFSPIntegration.svg)](https://badge.fury.io/py/docassemble.EFSPIntegration)

A docassemble extension that talks to [a proxy e-filing server](https://github.com/SuffolkLITLab/EfileProxyServer/) easily within a docassemble interview.

Main interviews of import:

* any_filing_interview.yml: allows you to make any type of filing, initial or subsequent
* admin_interview.yml: lets you handle admin / user functionality, outside of the context of cases and filings

## Config

Different parts of this package expect the below to be present in Docassemble's
config.

```yaml
efile proxy:
  # The URL where the Efile Proxy Server is running
  url: https:...
  # The Proxy Server's API Key (should be provided to you by the sever admins)
  api key: ...
  # If you're given an EFSP global fee waiver ID for your jurisdiction, put it here
  global waivers:
    illinois: ...
    massachusetts: ...
```

## Authors

Quinten Steenhuis (qsteenhuis@suffolk.edu)
Bryce Willey (bwilley@suffolk.edu)


### Optional case metadata

Including `case_search.yml` provides `case_type_name` and `case_category_name`
for both `search.found_case` and `search.found_cases[i]`. Lookups use each found
case's court, which may differ from the search court. Names are validated strings
or `None` when the service fails or metadata is missing; raw filing codes are
unchanged. Interview authors must distinguish unavailable metadata from a
negative eligibility decision and decide whether to retry or offer manual filing.

`case_metadata.case_labels(proxy, court_id, case_type, category)` exposes the same
normalization to Python callers. `clear_case_labels(search)` removes cached labels
from existing results without triggering missing docassemble variables. Call it
once before consuming labels in a new request or retry, and invalidate the
interview's derived decisions at the same time. Avoid repeatedly clearing labels
during dependency resolution for multiple results. The library does not assume
an interview-specific global object name or impose an eligibility policy.
