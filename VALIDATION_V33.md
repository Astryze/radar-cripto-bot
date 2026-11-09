# Validação do Radar 3.3

Base `4c76bbe7fd3789bd2f875cad6cbfcb98a573a2ad`.

- Validação local com Pytest, Ruff, compileall, YAML, actionlint e scanner de credenciais.
- Testes de Zealy, Galxe e Telegram usam respostas simuladas.
- A Galxe mantém o endpoint oficial GraphQL e registra resultado por Space.
  O [guia de fidelidade](https://docs.galxe.com/galxe-integration/guides/loyalty-program)
  documenta pontos da quest e placares. O coletor não consulta placares de
  participantes e separa pontos de valor resgatável.
- As integrações dependem de credenciais e escopos autorizados. Um catálogo
  parcial preserva os registros já coletados, com falhas por escopo.
- A consulta de evidências da 3.3 acrescenta classificação no relatório e exige
  comprovação de resgate sem taxa para novos alertas de custo zero.
- A execução manual oferece um teste Telegram separado do dry-run.
- O dry-run real da 3.2 permanece como referência histórica
  ([execução 42544039762](https://github.com/Astryze/radar-cripto-bot/actions/runs/42544039762)).
