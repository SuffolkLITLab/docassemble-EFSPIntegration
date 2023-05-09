# CHANGELOG

## Version v1.2.0

### Added

* Payments improvements, including a better UI and clearer user-text in [#203](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/203)
* Logs API by @BryceStevenWilley in [#199](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/199/commits/acb4c946d227359633fe85b145b690a0ff83dd08)

### Fixed

* Will actually log you out of the admin interview when you click logout (broken by [v1.1.0](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/blob/main/CHANGELOG.md#version-v110)) in [#203](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/203)
* Got integration tests working again, but only locally: [#199](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/199/commits/2283e46b71ba69c0e4bc6eefc8197942092c6c60)
  * Slightly cleaner integration testing in [#202](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/202)
* Trying to make better doc strings: [#190](https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/pull/190)

## Version v1.1.0

### Added

* there is now a "show password" checkbox below each password the user needs to enter, that
  will toggle the input type from "password" to "text", which allows the user to see the password
  they have entered so far.
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/bc7796ebde0ee595dc30f56f6923d2073eb47bff

### Changed

* Use DAStore to save the user's login token across interviews. Now, if a user logs into Tyler's system
  in one interview and then starts another separate interview, the second will automatically log them in
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/1b699881c8c234072547416efcf0b605e70d0323
* Shows Tyler's error message when trying to reset passwords, which do say if the email exists or not.
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/bc7796ebde0ee595dc30f56f6923d2073eb47bff

## Version v1.0.3

All changes are in https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/2dab0b3f0df55fba8442aa7ff6cfeee9b45f56fd.

### Fixed

* Avoid `None` errors when filters codes. Don't know why the name of a code would ever be null,
  but it did happen in production.

### Non-production-ready features

* Added a short message and spinning gif when forwarding to Tyler's payments site.

## Version v1.0.2

All changes are in https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/c01b09848196af0bce4bd674375c0a2ab2dd207e.

### Fixed

* Fewer crashes in `chain_xml`
* Don't crash if you can't find the case title

### Changed

* Case search can sometimes find cases in subcourts; i.e. if you search for cases in the
  `peoria` court, you can find cases from `peoriacr`. The ultimate court you need to file into
  needs to be the court the case is from, not what you searched in. To fix this, we now get the
  `court_id` from the case details, and use that for `found_cases[i].court_id`.
  instead of the court you searched in. Added a note for this in `case_search.yml`

## Version v1.0.1

### Fixed

* Courts have a multitude of typos in their code names, including extra spaces.
  We now strip out leading and trailing spaces from code names when trying to match
  exact names.
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/0b3715b7764d8b017a0d521589cb9742560405fc
* Have better defaults for `.document_type`, `.filing_type`, and document and filing filters
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/a917531694f567d7a0e2c405a3a4d89b56fa0e2e
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/911bc7872203cf4c5a4c8461f1fccca0e4f84868

### Changed

* Tryng to start the resend activation action before the
  registration action has technically fiinshed queues up the next
  action, but stays on the current screen, making it seem like nothing
  is happenning. Instead, we just note that users can resend their actiavation
  email from the home screen (the next screen in the interview)
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/5e49107becbe89c4652cdbe4589da1f911024afa
* Removed the "restart" button from the in-interview password reset flow. Users can just go back.
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/3db90f74c536316a6f3204a6ee0dd57ddc4de2d0

### Not-pro-ready features
* stopped DA from showing "Input not processed" when we are adding
  waiver and income types
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/232d60332e6c1e23eca9b66403f7b5f4644c7f25
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/751d42694cda4d0dcec5e473801801cd9cf8d339
 
### Internal
* Use SuffolkLITLab/ALActions for the GitHub actions that run tests
  * https://github.com/SuffolkLITLab/docassemble-EFSPIntegration/commit/0fe84c836ea29b8b8f6bd4148c837eb09861a63e

## Version v1.0.0

First 1.0 release! Previous versions aren't considered to be
documented, so earlier versions won't be listed. 

