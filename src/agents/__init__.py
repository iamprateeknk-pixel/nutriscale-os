"""NutriScale Agent Layer — real agents on top of the engines.
Every agent: reads data -> thinks (rules today; an LLM plugs into the same place once a key is added) ->
creates a proposal -> gets a tier from the Approval Engine -> stored in the DB with WAITING status.
"""
