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
