# REAL_DOCS_EVAL

Ниже описаны ожидаемые результаты для выбранных реальных документов. Это не юридическая экспертиза, а eval-разметка для проверки baseline-логики: классификация, impact, matching клиентов, уведомления, evidence и review.

## 001_personal_data_1066_2022.txt

- Source original: `1.txt`
- Title: Постановление Правительства Российской Федерации от 15.06.2022 № 1066 "О размещении физическими лицами своих биометрических персональных данных в единой информационной системе персональных данных, обеспечивающей обработку, включая сбор и хранение, биометрических персональных данных, их проверку и передачу информации о степени их соответствия предоставленным биометрическим персональным данным физического лица"
- Date: 2022-06-17
- Expected document_type: `постановление`
- Expected domain: `personal_data`
- Expected topics: персональные данные, биометрия, идентификация
- Expected impact_level: `medium`
- Relevant client tags: personal_data, biometrics, ecommerce, saas, online_service
- Non-relevant client tags: fuel, securities_market, restaurant_no_pd
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: персональных данных, биометрических персональных данных

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 002_personal_data_1046_2021.txt

- Source original: `2.txt`
- Title: Постановление Правительства Российской Федерации от 29.06.2021 № 1046 "О федеральном государственном контроле (надзоре) за обработкой персональных данных"
- Date: 2021-06-30
- Expected document_type: `постановление`
- Expected domain: `personal_data`
- Expected topics: персональные данные, биометрия, идентификация
- Expected impact_level: `medium`
- Relevant client tags: personal_data, biometrics, ecommerce, saas, online_service
- Non-relevant client tags: fuel, securities_market, restaurant_no_pd
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: персональных данных, обработкой персональных данных

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 003_personal_data_1801_2021.txt

- Source original: `Разные документы.txt#31`
- Title: Постановление Правительства Российской Федерации от 20.10.2021 № 1801 "Об утверждении Правил идентификации пользователей информационно-телекоммуникационной сети "Интернет" организатором сервиса обмена мгновенными сообщениями"
- Date: 2021-10-21
- Expected document_type: `постановление`
- Expected domain: `personal_data`
- Expected topics: персональные данные, биометрия, идентификация
- Expected impact_level: `medium`
- Relevant client tags: personal_data, biometrics, ecommerce, saas, online_service
- Non-relevant client tags: fuel, securities_market, restaurant_no_pd
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: идентификацию пользователей

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 004_aml_105-fz_2025.txt

- Source original: `Разные документы.txt#10`
- Title: Федеральный закон от 23.05.2025 № 105-ФЗ "О внесении изменений в отдельные законодательные акты Российской Федерации"
- Date: 2025-05-23
- Expected document_type: `федеральный закон`
- Expected domain: `aml`
- Expected topics: ПОД/ФТ, идентификация клиентов, подозрительные операции
- Expected impact_level: `high`
- Relevant client tags: aml_risk, cash_heavy, bank, payment_service, foreign_financial_org
- Non-relevant client tags: neutral, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: противодействии легализации, финансированию терроризма, внесены изменения

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 005_aml_165-fz_2021.txt

- Source original: `5.txt`
- Title: Федеральный закон от 11.06.2021 № 165-ФЗ "О внесении изменений в Федеральный закон "О противодействии легализации (отмыванию) доходов, полученных преступным путем, и финансированию терроризма"
- Date: 2021-06-11
- Expected document_type: `федеральный закон`
- Expected domain: `aml`
- Expected topics: ПОД/ФТ, идентификация клиентов, подозрительные операции
- Expected impact_level: `high`
- Relevant client tags: aml_risk, cash_heavy, bank, payment_service, foreign_financial_org
- Non-relevant client tags: neutral, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: противодействии легализации, финансированию терроризма, оружия массового уничтожения

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 006_aml_2838-r_2023.txt

- Source original: `6.txt`
- Title: Распоряжение Правительства Российской Федерации от 14.10.2023 № 2838-р
- Date: 2023-10-24
- Expected document_type: `распоряжение`
- Expected domain: `aml`
- Expected topics: ПОД/ФТ, идентификация клиентов, подозрительные операции
- Expected impact_level: `high`
- Relevant client tags: aml_risk, cash_heavy, bank, payment_service, foreign_financial_org
- Non-relevant client tags: neutral, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: идентификации клиента, бенефициарного владельца

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 007_aml_423-fz_2021.txt

- Source original: `8.txt`
- Title: Федеральный закон от 21.12.2021 № 423-ФЗ "О внесении изменений в отдельные законодательные акты Российской Федерации"
- Date: 2021-12-21
- Expected document_type: `федеральный закон`
- Expected domain: `aml`
- Expected topics: ПОД/ФТ, идентификация клиентов, подозрительные операции
- Expected impact_level: `high`
- Relevant client tags: aml_risk, cash_heavy, bank, payment_service, foreign_financial_org
- Non-relevant client tags: neutral, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: подозрительных операций

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 008_foreign_trade_currency_control_821_2022.txt

- Source original: `12.txt`
- Title: Постановление Правительства Российской Федерации от 06.05.2022 № 821 "О внесении изменений в Правила осуществления акционерным обществом "Российский экспортный центр" деятельности по поддержке экспорта и импорта, а также взаимодействия с федеральными органами исполнительной власти, органами и агентами валютного контроля и Государственной корпорацией по атомной энергии "Росатом"
- Date: 2022-05-07
- Expected document_type: `постановление`
- Expected domain: `foreign_trade_currency_control`
- Expected topics: ВЭД, валютное регулирование, валютный контроль, экспорт, импорт
- Expected impact_level: `medium`
- Relevant client tags: foreign_trade, import, export, currency_control, customs
- Non-relevant client tags: saas_local, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: валютного контроля, экспорта и импорта, внешнеторговой деятельности

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 009_foreign_trade_currency_control_2020_2021.txt

- Source original: `Разные документы.txt#40`
- Title: Постановление Правительства Российской Федерации от 24.11.2021 № 2020 "Об утверждении Правил проверки (идентификации) таможенным органом охранной маркировки на музыкальных инструментах или смычках, включенных в состав Музейного фонда Российской Федерации, маркировки, нанесенной в соответствии со статьей 35.13 Закона Российской Федерации "О вывозе и ввозе культурных ценностей", а также паспортов и заключений (разрешительных документов) на временный вывоз музыкальных инструментов или смычков"
- Date: 2021-11-26
- Expected document_type: `постановление`
- Expected domain: `foreign_trade_currency_control`
- Expected topics: ВЭД, валютное регулирование, валютный контроль, экспорт, импорт
- Expected impact_level: `medium`
- Relevant client tags: foreign_trade, import, export, currency_control, customs
- Non-relevant client tags: saas_local, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: таможенным органом

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 010_foreign_trade_currency_control_214-rp_2023.txt

- Source original: `10.txt`
- Title: Распоряжение Президента Российской Федерации от 03.07.2023 № 214-рп "О внесении изменений в состав межведомственной рабочей группы по выработке новых механизмов в сфере валютного регулирования и международных расчетов, утвержденный распоряжением Президента Российской Федерации от 9 мая 2022 г. № 134-рп"
- Date: 2023-07-03
- Expected document_type: `распоряжение президента`
- Expected domain: `foreign_trade_currency_control`
- Expected topics: ВЭД, валютное регулирование, валютный контроль, экспорт, импорт
- Expected impact_level: `medium`
- Relevant client tags: foreign_trade, import, export, currency_control, customs
- Non-relevant client tags: saas_local, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: валютного регулирования

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 011_financial_market_securities_469_2026.txt

- Source original: `previous:ukaz_469_public_securities_2026.txt`
- Title: Указ Президента Российской Федерации от 02.07.2026 № 469 "О временных мерах, связанных с публичным обращением ценных бумаг"
- Date: 2026-07-02
- Expected document_type: `указ`
- Expected domain: `financial_market_securities`
- Expected topics: финансовый рынок, ценные бумаги, инвестиционные инструменты
- Expected impact_level: `medium`
- Relevant client tags: broker, securities_market, issuer, investment_platform, cfa
- Non-relevant client tags: ecommerce, restaurant, fuel
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: рынке ценных бумаг, вступает в силу

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 012_fuel_excise_825_2026.txt

- Source original: `previous:postanovlenie_825_fuel_excise_2026.txt`
- Title: Постановление Правительства Российской Федерации от 02.07.2026 № 825 "О внесении изменений в постановление Правительства Российской Федерации от 29 апреля 2021 г. № 669"
- Date: 2026-07-02
- Expected document_type: `постановление`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: автомобильного бензина, дизельного топлива, нефтяного сырья, акциз, налогового периода по акцизам

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 013_fuel_excise_623_2022.txt

- Source original: `Разные документы.txt#01`
- Title: Постановление Правительства Российской Федерации от 08.04.2022 № 623 "О приостановлении действия пункта 7 Правил определения минимальной величины объема автомобильного бензина класса 5 и (или) дизельного топлива класса 5, произведенных в том числе по договору об оказании налогоплательщику услуг по переработке нефтяного сырья и реализованных налогоплательщиком, имеющим свидетельство о регистрации лица, совершающего операции по переработке нефтяного сырья, и (или) иным лицом, входящим в одну группу лиц с таким налогоплательщиком в соответствии с антимонопольным законодательством Российской Федерации, в налоговом периоде на биржевых торгах, проводимых биржей (биржами)"
- Date: 2022-04-11
- Expected document_type: `постановление`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: автомобильного бензина, дизельного топлива, нефтяного сырья, биржевых торгах

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 014_fuel_excise_1728_2021.txt

- Source original: `Разные документы.txt#09`
- Title: Постановление Правительства Российской Федерации от 11.10.2021 № 1728 "О внесении изменений в постановление Правительства Российской Федерации от 10 марта 2021 г. № 341"
- Date: 2021-10-13
- Expected document_type: `постановление`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: акциз, налогового периода по акцизам, вступает в силу, внесены изменения

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 015_fuel_excise_520-fz_2023.txt

- Source original: `Разные документы.txt#02`
- Title: Федеральный закон от 02.11.2023 № 520-ФЗ "О внесении изменений в статьи 96-6 и 220-1 Бюджетного кодекса Российской Федерации и отдельные законодательные акты Российской Федерации, приостановлении действия отдельных положений Бюджетного кодекса Российской Федерации и об установлении особенностей исполнения бюджетов бюджетной системы Российской Федерации в 2024 году"
- Date: 2023-11-02
- Expected document_type: `федеральный закон`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: автомобильного бензина, дизельного топлива

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 016_fuel_excise_136-fz_2023.txt

- Source original: `Разные документы.txt#07`
- Title: Федеральный закон от 27.04.2023 № 136-ФЗ "О внесении изменений в статьи 342-6 и 343-2 части второй Налогового кодекса Российской Федерации и статью 3-1 Закона Российской Федерации "О таможенном тарифе"
- Date: 2023-04-27
- Expected document_type: `федеральный закон`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: нефтяного сырья, нефть сырую

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 017_fuel_excise_1683_2025.txt

- Source original: `Разные документы.txt#05`
- Title: Постановление Правительства Российской Федерации от 29.10.2025 № 1683 "Об оказании поддержки отрасли черной металлургии"
- Date: 2025-10-30
- Expected document_type: `постановление`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: акциз, срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 018_fuel_excise_2553_2023.txt

- Source original: `Разные документы.txt#08`
- Title: Постановление Правительства Российской Федерации от 30.12.2022 № 2553 "Об утверждении Правил формирования и использования бюджетных ассигнований федерального бюджета на финансовое обеспечение социально-экономического развития Арктической зоны Российской Федерации за счет налоговых поступлений от реализации на территории Арктической зоны Российской Федерации инвестиционных проектов и о внесении изменений в некоторые акты Правительства Российской Федерации"
- Date: 2023-01-04
- Expected document_type: `постановление`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: акциз

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 019_fuel_excise_321-fz_2020.txt

- Source original: `Разные документы.txt#04`
- Title: Федеральный закон от 15.10.2020 № 321-ФЗ "О внесении изменений в часть вторую Налогового кодекса Российской Федерации в части введения обратного акциза на этан, сжиженные углеводородные газы и инвестиционного коэффициента, применяемого при определении размера обратного акциза на нефтяное сырье"
- Date: 2020-10-15
- Expected document_type: `федеральный закон`
- Expected domain: `fuel_excise`
- Expected topics: топливный рынок, нефтепереработка, акцизы, биржевые торги
- Expected impact_level: `medium`
- Relevant client tags: fuel, oil_products, oil_processing, excise, exchange_trading
- Non-relevant client tags: ecommerce, saas, restaurant, personal_data_only
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: акциз

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 020_payments_digital_ruble_136_2026.txt

- Source original: `Разные документы.txt#18`
- Title: Постановление Правительства Российской Федерации от 14.02.2026 № 136 "Об утверждении Правил взаимодействия операторов по переводу денежных средств, операторов электронных денежных средств и операторов подвижной радиотелефонной связи с заинтересованными федеральными государственными органами"
- Date: 2026-02-21
- Expected document_type: `постановление`
- Expected domain: `payments_digital_ruble`
- Expected topics: платежи, переводы денежных средств, цифровой рубль, банковские карты
- Expected impact_level: `medium`
- Relevant client tags: payment_service, acquiring, sbp, digital_ruble, bank_card, operator_transfer
- Non-relevant client tags: fuel, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: переводу денежных средств, операторов по переводу денежных средств, электронных денежных средств

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 021_payments_digital_ruble_1103_2021.txt

- Source original: `Разные документы.txt#33`
- Title: Постановление Правительства Российской Федерации от 30.06.2021 № 1103 "Об утверждении Правил предоставления субсидий из федерального бюджета российским кредитным организациям на возмещение затрат субъектам малого и среднего предпринимательства на оплату банковских комиссий при осуществлении перевода денежных средств физическими лицами в пользу субъектов малого и среднего предпринимательства в оплату товаров (работ, услуг) в сервисе быстрых платежей платежной системы Банка России"
- Date: 2021-07-12
- Expected document_type: `постановление`
- Expected domain: `payments_digital_ruble`
- Expected topics: платежи, переводы денежных средств, цифровой рубль, банковские карты
- Expected impact_level: `medium`
- Relevant client tags: payment_service, acquiring, sbp, digital_ruble, bank_card, operator_transfer
- Non-relevant client tags: fuel, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: платежной системы Банка России, утверждены Правила

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 022_payments_digital_ruble_1200_2020.txt

- Source original: `Разные документы.txt#20`
- Title: Постановление Правительства Российской Федерации от 10.08.2020 № 1200 "Об утверждении Правил предоставления в 2020 году из федерального бюджета субсидии акционерному обществу "Национальная система платежных карт" на стимулирование доступных внутренних туристических поездок через возмещение части стоимости оплаченной туристской услуги"
- Date: 2020-08-11
- Expected document_type: `постановление`
- Expected domain: `payments_digital_ruble`
- Expected topics: платежи, переводы денежных средств, цифровой рубль, банковские карты
- Expected impact_level: `medium`
- Relevant client tags: payment_service, acquiring, sbp, digital_ruble, bank_card, operator_transfer
- Non-relevant client tags: fuel, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: национального платежного инструмента, срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 023_payments_digital_ruble_759_2021.txt

- Source original: `Разные документы.txt#19`
- Title: Постановление Правительства Российской Федерации от 19.05.2021 № 759 "Об утверждении Правил предоставления в 2021 году из федерального бюджета субсидии акционерному обществу "Национальная система платежных карт" на реализацию программы поддержки доступных внутренних туристских поездок в организации отдыха детей и их оздоровления через возмещение части стоимости оплаченной туристской услуги"
- Date: 2021-05-21
- Expected document_type: `постановление`
- Expected domain: `payments_digital_ruble`
- Expected topics: платежи, переводы денежных средств, цифровой рубль, банковские карты
- Expected impact_level: `medium`
- Relevant client tags: payment_service, acquiring, sbp, digital_ruble, bank_card, operator_transfer
- Non-relevant client tags: fuel, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: национального платежного инструмента, срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 024_payments_digital_ruble_72_2023.txt

- Source original: `Разные документы.txt#34`
- Title: Указ Президента Российской Федерации от 06.02.2023 № 72 "Об особом порядке проведения расчетов между некоторыми юридическими лицами - резидентами при осуществлении внешнеэкономической деятельности"
- Date: 2023-02-06
- Expected document_type: `указ`
- Expected domain: `payments_digital_ruble`
- Expected topics: платежи, переводы денежных средств, цифровой рубль, банковские карты
- Expected impact_level: `medium`
- Relevant client tags: payment_service, acquiring, sbp, digital_ruble, bank_card, operator_transfer
- Non-relevant client tags: fuel, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: переводу денежных средств

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 025_lending_consumer_credit_9-fz_2025.txt

- Source original: `Разные документы.txt#14`
- Title: Федеральный закон от 13.02.2025 № 9-ФЗ "О внесении изменений в отдельные законодательные акты Российской Федерации"
- Date: 2025-02-13
- Expected document_type: `федеральный закон`
- Expected domain: `lending_consumer_credit`
- Expected topics: кредитование, потребительский кредит, банковская деятельность
- Expected impact_level: `medium`
- Relevant client tags: bank, lending, consumer_credit, financial_service
- Non-relevant client tags: fuel, culture, restaurant
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: потребительского кредита, договора потребительского кредита, кредитная организация обязана фиксировать, внесены изменения

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 026_tax_reporting_371-fz_2021.txt

- Source original: `Разные документы.txt#24`
- Title: Федеральный закон от 19.11.2021 № 371-ФЗ "О внесении изменений в статьи 25-12 и 25-12-1 части первой и статью 288-2 части второй Налогового кодекса Российской Федерации"
- Date: 2021-11-19
- Expected document_type: `федеральный закон`
- Expected domain: `tax_reporting`
- Expected topics: налоги, налоговый контроль, отчетность, ФНС
- Expected impact_level: `medium`
- Relevant client tags: tax_reporting, accounting, corporate_tax, investment_project, cash_declaration
- Non-relevant client tags: culture, education, health_social
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: Налогового кодекса, налоговой проверки, налога на прибыль, вступает в силу

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 027_tax_reporting_48-fz_2022.txt

- Source original: `Разные документы.txt#23`
- Title: Федеральный закон от 09.03.2022 № 48-ФЗ "О внесении изменений в Федеральный закон "О добровольном декларировании физическими лицами активов и счетов (вкладов) в банках и о внесении изменений в отдельные законодательные акты Российской Федерации"
- Date: 2022-03-09
- Expected document_type: `федеральный закон`
- Expected domain: `tax_reporting`
- Expected topics: налоги, налоговый контроль, отчетность, ФНС
- Expected impact_level: `medium`
- Relevant client tags: tax_reporting, accounting, corporate_tax, investment_project, cash_declaration
- Non-relevant client tags: culture, education, health_social
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: налоговый орган, декларации, срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 028_tax_reporting_409_2024.txt

- Source original: `Разные документы.txt#25`
- Title: Постановление Правительства Российской Федерации от 01.04.2024 № 409 "Об особенностях неприменения ответственности в 2024 году к лицам, состоящим на учете в налоговых органах по месту нахождения (месту жительства) на территориях Донецкой Народной Республики, Луганской Народной Республики, Запорожской области, Херсонской области"
- Date: 2024-04-02
- Expected document_type: `постановление`
- Expected domain: `tax_reporting`
- Expected topics: налоги, налоговый контроль, отчетность, ФНС
- Expected impact_level: `medium`
- Relevant client tags: tax_reporting, accounting, corporate_tax, investment_project, cash_declaration
- Non-relevant client tags: culture, education, health_social
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: налогоплательщиков, декларации, ответственности

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 029_info_security_it_1425_2020.txt

- Source original: `Разные документы.txt#39`
- Title: Постановление Правительства Российской Федерации от 14.09.2020 № 1425 "Об утверждении Правил проведения экспертизы культурных ценностей и направления экспертом экспертного заключения в Министерство культуры Российской Федерации, а также критериев отнесения движимых предметов к культурным ценностям и отнесения культурных ценностей к культурным ценностям, имеющим особое историческое, художественное, научное или культурное значение"
- Date: 2020-09-17
- Expected document_type: `постановление`
- Expected domain: `info_security_it`
- Expected topics: информационная безопасность, информационные системы, цифровые технологии, идентификация пользователей
- Expected impact_level: `medium`
- Relevant client tags: it_system, info_security, online_service, messenger, digital_platform
- Non-relevant client tags: fuel_only, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: информационно-телекоммуникационной сети, утверждены Правила, срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 030_info_security_it_152-fz_2023.txt

- Source original: `4.txt`
- Title: Федеральный закон от 28.04.2023 № 152-ФЗ "О внесении изменений в статьи 3.5 и 14.55-2 Кодекса Российской Федерации об административных правонарушениях"
- Date: 2023-04-28
- Expected document_type: `федеральный закон`
- Expected domain: `info_security_it`
- Expected topics: информационная безопасность, информационные системы, цифровые технологии, идентификация пользователей
- Expected impact_level: `medium`
- Relevant client tags: it_system, info_security, online_service, messenger, digital_platform
- Non-relevant client tags: fuel_only, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: информационно-телекоммуникационной сети

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 031_info_security_it_1933_2025.txt

- Source original: `Разные документы.txt#26`
- Title: Постановление Правительства Российской Федерации от 28.11.2025 № 1933 "О государственной информационной системе по предупреждению, выявлению и пресечению ограничивающих конкуренцию соглашений"
- Date: 2025-12-09
- Expected document_type: `постановление`
- Expected domain: `info_security_it`
- Expected topics: информационная безопасность, информационные системы, цифровые технологии, идентификация пользователей
- Expected impact_level: `medium`
- Relevant client tags: it_system, info_security, online_service, messenger, digital_platform
- Non-relevant client tags: fuel_only, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: цифровых технологий

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 032_info_security_it_63_2021.txt

- Source original: `Разные документы.txt#29`
- Title: Постановление Правительства Российской Федерации от 28.01.2021 № 63 "О приостановлении действия отдельных положений постановления Правительства Российской Федерации от 8 июня 2018 г. № 658"
- Date: 2021-01-30
- Expected document_type: `постановление`
- Expected domain: `info_security_it`
- Expected topics: информационная безопасность, информационные системы, цифровые технологии, идентификация пользователей
- Expected impact_level: `medium`
- Relevant client tags: it_system, info_security, online_service, messenger, digital_platform
- Non-relevant client tags: fuel_only, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: информационной безопасности

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 033_info_security_it_72-fz_2025.txt

- Source original: `Разные документы.txt#32`
- Title: Федеральный закон от 07.04.2025 № 72-ФЗ "О внесении изменений в статью 12 Федерального закона "О противодействии экстремистской деятельности" и Федеральный закон "О рекламе"
- Date: 2025-04-07
- Expected document_type: `федеральный закон`
- Expected domain: `info_security_it`
- Expected topics: информационная безопасность, информационные системы, цифровые технологии, идентификация пользователей
- Expected impact_level: `medium`
- Relevant client tags: it_system, info_security, online_service, messenger, digital_platform
- Non-relevant client tags: fuel_only, culture, education
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: информационных технологиях

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 034_product_marking_trade_137_2022.txt

- Source original: `15.txt`
- Title: Постановление Правительства Российской Федерации от 09.02.2022 № 137 "О проведении на территории Российской Федерации эксперимента по маркировке отдельных видов медицинских изделий средствами идентификации"
- Date: 2022-02-10
- Expected document_type: `постановление`
- Expected domain: `product_marking_trade`
- Expected topics: маркировка товаров, товарный оборот, импорт, медицинские изделия
- Expected impact_level: `medium`
- Relevant client tags: product_marking, import, medical_devices, wholesale, retail
- Non-relevant client tags: bank_only, securities_market, culture
- Notification behavior: `only_relevant_clients`
- Review state: `needs_review`
- Evidence should include: маркировке, средствами идентификации, медицинских изделий, производителями, импортерами

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 035_neutral_no_match_1762_2020.txt

- Source original: `Разные документы.txt#35`
- Title: Постановление Правительства Российской Федерации от 30.10.2020 № 1762 "О государственной социальной поддержке в 2020 - 2021 годах медицинских и иных работников медицинских и иных организаций (их структурных подразделений), оказывающих медицинскую помощь (участвующих в оказании, обеспечивающих оказание медицинской помощи) по диагностике и лечению новой коронавирусной инфекции (COVID-19), медицинских работников, контактирующих с пациентами с установленным диагнозом новой коронавирусной инфекции (COVID-19), внесении изменений во Временные правила учета информации в целях предотвращения распространения новой коронавирусной инфекции (COVID-19) и признании утратившими силу отдельных актов Правительства Российской Федерации"
- Date: 2020-10-31
- Expected document_type: `постановление`
- Expected domain: `neutral_no_match`
- Expected topics: нейтральное регулирование, no-match
- Expected impact_level: `low`
- Relevant client tags: none
- Non-relevant client tags: ecommerce, saas, broker, fuel, payment_service
- Notification behavior: `none`
- Review state: `needs_review`
- Evidence should include: утверждены Правила

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 036_neutral_no_match_1342_2022.txt

- Source original: `Разные документы.txt#42`
- Title: Постановление Правительства Российской Федерации от 28.07.2022 № 1342 "О мерах по реализации Указа Президента Российской Федерации от 9 марта 2022 г. № 102 "О премиях лучшим преподавателям в области музыкального искусства"
- Date: 2022-07-29
- Expected document_type: `постановление`
- Expected domain: `neutral_no_match`
- Expected topics: нейтральное регулирование, no-match
- Expected impact_level: `low`
- Relevant client tags: none
- Non-relevant client tags: ecommerce, saas, broker, fuel, payment_service
- Notification behavior: `none`
- Review state: `needs_review`
- Evidence should include: утверждены Правила

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 037_neutral_no_match_2339_2021.txt

- Source original: `Разные документы.txt#27`
- Title: Постановление Правительства Российской Федерации от 17.12.2021 № 2339 "О реализации пилотного проекта по оказанию услуг по комплексной реабилитации и абилитации детей-инвалидов"
- Date: 2021-12-22
- Expected document_type: `постановление`
- Expected domain: `neutral_no_match`
- Expected topics: нейтральное регулирование, no-match
- Expected impact_level: `low`
- Relevant client tags: none
- Non-relevant client tags: ecommerce, saas, broker, fuel, payment_service
- Notification behavior: `none`
- Review state: `needs_review`
- Evidence should include: утверждены Правила

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 038_neutral_no_match_1390-r_2021.txt

- Source original: `Разные документы.txt#03`
- Title: Распоряжение Правительства Российской Федерации от 27.05.2021 № 1390-р
- Date: 2021-05-28
- Expected document_type: `распоряжение`
- Expected domain: `neutral_no_match`
- Expected topics: нейтральное регулирование, no-match
- Expected impact_level: `low`
- Relevant client tags: none
- Non-relevant client tags: ecommerce, saas, broker, fuel, payment_service
- Notification behavior: `none`
- Review state: `needs_review`
- Evidence should include: срок

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

## 039_neutral_no_match_1897_2020.txt

- Source original: `Разные документы.txt#41`
- Title: Постановление Правительства Российской Федерации от 23.11.2020 № 1897 "О внесении изменений в государственную программу Российской Федерации "Развитие физической культуры и спорта"
- Date: 2020-12-01
- Expected document_type: `постановление`
- Expected domain: `neutral_no_match`
- Expected topics: нейтральное регулирование, no-match
- Expected impact_level: `low`
- Relevant client tags: none
- Non-relevant client tags: ecommerce, saas, broker, fuel, payment_service
- Notification behavior: `none`
- Review state: `needs_review`
- Evidence should include: at least one source fragment

Actual before changes:
- Заполнить после первого прогона системы.

Decision:
- OK / needs rule update / keep as no-match control.

