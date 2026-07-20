.. SlickBet documentation master file.
   Pattern mirrors slick-tune docs (https://github.com/slickml/slick-tune/tree/master/docs).

SlickBet ⚽ Documentation
*************************

|build_status| |codecov| |downloads| |github_stars| |slack_invite| |twitter_url|

----

🧠 SlickBet ⚽ Philosophy
-------------------------

`SlickBet <https://github.com/slickml/slick-bet>`_ screens soccer matches via the Livescore API,
scores each fixture with a 12-factor statistical model, and ranks betting opportunities —
including safer double-chance picks. Same SlickML spirit: prototype fast, keep axes clear,
and measure with backtests.

.. code-block:: text

   fixtures  ×  model  ×  filters  ×  backtest  ×  export

.. grid:: 1 2 2 2
    :gutter: 3
    :margin: 0
    :padding: 3 4 0 0

    .. grid-item-card:: :doc:`🛠 Installation <pages/installation>`
        :link: pages/installation
        :link-type: doc

        Requirements and how to set up your Python environment with ``uv`` ...

    .. grid-item-card:: :doc:`📌 Quick Start <pages/quick_start>`
        :link: pages/quick_start
        :link-type: doc

        Screen leagues, backtest, and tune weights in a few commands ...

    .. grid-item-card:: :doc:`🎯 API Reference <pages/api>`
        :link: pages/api
        :link-type: doc

        Explore the SlickBet API and source modules ...

----

🧑‍💻🤝 Become a Contributor
----------------------------

SlickBet is part of the SlickML open-source family. Join our
`Slack <https://www.slickml.com/slack-invite>`_ to talk with the team.

.. toctree::
   :maxdepth: 2
   :hidden:

   pages/installation
   pages/quick_start
   pages/api
   pages/license
   pages/contact_us


.. |build_status| image:: https://github.com/slickml/slick-bet/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/slickml/slick-bet/actions/workflows/ci.yml
   :alt: build

.. |codecov| image:: https://codecov.io/gh/slickml/slick-bet/graph/badge.svg
   :target: https://codecov.io/gh/slickml/slick-bet
   :alt: codecov

.. |downloads| image:: https://pepy.tech/badge/slickbet
   :target: https://pepy.tech/project/slickbet
   :alt: downloads

.. |github_stars| image:: https://img.shields.io/github/stars/slickml/slick-bet?style=social
   :target: https://github.com/slickml/slick-bet
   :alt: stars

.. |slack_invite| image:: https://badgen.net/badge/Join/SlickML%20Slack/purple?icon=slack
   :target: https://www.slickml.com/slack-invite
   :alt: slack

.. |twitter_url| image:: https://img.shields.io/twitter/url?style=social&url=https%3A%2F%2Ftwitter.com%2FSlickML
   :target: https://twitter.com/slickml
   :alt: twitter
