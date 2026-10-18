# Roadmap

What is planned, by target version. What has shipped lives in [CHANGELOG.md](CHANGELOG.md).

## 0.5.0

- OAuth authentication support.
- Email notifications for new releases and comments, with tunable preferences.
- Paginated admin revision list (`REVISION_PER_PAGE` is defined but every revision is loaded).
- Generic `/api` error answers, the exception and the internal paths going to the server log instead.
- Screenshot keys of the Breakout and Sokoban samples, once the engine CI captures them.
- Engine side, in the Owl repository: a `PublishShowcase` CI action pushing the screenshots, and `push_release` on a release tag.
- A development image with ruff, so the lint runs like the tests.
