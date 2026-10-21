# Chartink feature parity audit

**Purpose:** implement equivalent capabilities for US equities without copying Chartink source code, assets, or private APIs. This inventory is based on publicly observable Chartink screener pages as of 2026-10-21, not a claim of access to Chartink internals. Some functions are subscription-gated and their full behavior cannot be established from public pages alone.

## Evidence used
- [Chartink Scanner Help](https://chartink.com/screener/help): filter clauses, stock universe selection, Magic Filters, live-alert promotion.
- [Chartink Data/Scanner UI](https://chartink.com/screener/data): minute through yearly timeframes, indicators and number/indicator comparisons, scan history/backtest view, bars/stocks tabs, CSV.
- [Chartink example scanner](https://chartink.com/screener/core-chartink-scanner): multi-clause scans, SMA/EMA, volume averages, highest/high lookbacks, Magic Filter prompt.
- [Chartink multi-entry example](https://chartink.com/screener/multi-entries): nested groups, AND/OR behavior, multiple timeframes and technical indicators.
- [Chartink app example](https://chartink.com/screener/app): historical bar offsets, candlestick-pattern examples and multi-condition scans.

## Capability matrix

| Capability observed in Chartink | Project status | Notes |
|---|---|---|
| US equity symbols / custom symbol list | Partial | User supplies tickers; no comprehensive exchange master yet |
| Filter builder with number/indicator comparisons | Partial | Backend rule engine supports both; UI is still a basic editor |
| AND/OR conditions and nested groups | Backend partial | Engine/API supports nested groups; nested-group editor is not in UI |
| Bar offsets / previous candles | Backend partial | Rule API supports offset; UI does not expose it yet |
| Count a condition over a lookback | Backend partial | Rule API supports count + lookback; UI does not expose it yet |
| Technical indicators | Partial | SMA, EMA, WMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, OBV, VWAP, ROC, CCI, ADX and DI available in engine |
| Multiple candle intervals | Partial | API/UI selection added; provider plan and interval entitlement must be verified |
| Multiple timeframes within one scan | Not implemented | Requires independent frame retrieval and aligned evaluation per rule |
| Magic / natural-language scan generation | Not implemented | Needs a safe rule parser and verification against explicit rules |
| Candle patterns | Not implemented | Requires definitions and tests for each pattern |
| Save and reload scans | Basic | Local SQLite persistence; no users, permissions, cloud sync or share links |
| Shareable scan URLs | Not implemented | Needs stable public/private scan IDs and access control |
| Backtest historical signals | Basic | API and UI count signals across provider bars; no equity curve, fills, slippage or benchmark |
| Backtest charts and click-through historical constituents | Not implemented | Requires a charting and history UI |
| Market chart, OHLC candles, chart indicators and drawings | Not implemented | Separate charting subsystem |
| Live/recurring alerts | Not implemented | Needs scheduler/worker, notification delivery, retries and alert state |
| Sector, industry, market-cap and fundamentals filters | Not implemented | Needs a reliable licensed US fundamentals and classification source |
| Broad built-in universes / exchange filters | Not implemented | Needs a maintained ticker/exchange master |
| CSV export | Partial | Exports matched latest scan rows |
| Accounts, authentication and scan ownership | Not implemented | Required before exposing saved scans publicly |
| Production deployment, cache and rate-limit controls | Not implemented | Required before public use |

## Engineering constraints
- The Twelve Data API key must remain server-side.
- A configured API key does not prove that the selected symbol, interval or history depth is available on the account.
- Intraday calls and larger universes can consume API credits quickly. Add provider-aware caching and throttling before broad scans.
- Backtests based on currently returned candles are signal research only. Do not treat them as execution-grade results without point-in-time data, split/dividend handling, transaction costs, slippage and a defined fill model.
- This independent application must not bypass Chartink authentication, scrape private endpoints, or reuse private user data. Use publicly observable pages and authorized test credentials only.

## Recommended implementation order
1. Stabilize and test the current API/indicator engine and Twelve Data integration.
2. Complete rule-editor controls for period, offsets, count windows, nested groups and indicator parameters.
3. Add a symbol directory and universe filters; confirm US exchange and fundamentals data sources.
4. Build aligned multi-timeframe evaluation and a historical backtest chart.
5. Add accounts, scan ownership, share links and saved-scan management.
6. Add scheduled/live alerts with a background queue and notification preferences.
7. Add a chart workspace, drawing tools and Magic Filter parsing.
8. Deploy with secrets, caching, observability, quotas, authentication and CI checks.

This checklist is intentionally honest: a fully faithful clone is not complete until every row has an implementation and a testable acceptance criterion.