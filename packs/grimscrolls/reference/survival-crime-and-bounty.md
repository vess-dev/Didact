---
id: survival-crime-and-bounty
title: "Crime & Bounty"
tags: [survival, crime-and-bounty]
source: surviving-tamriel/crime-and-bounty
mechanics: [crime, arrest]
---
Every hold, county, and Great House keeps its own ledger, and none of them share. When you're seen breaking the law — or a witness lives to describe you — the GM starts or shortens a pressure pool for that jurisdiction: *6d The Guards Know Your Face* for a theft or a brawl, *4d* for blood. Roll it whenever you show yourself in that hold's towns, and whenever you add to the list. No witness, no bounty; the guards are strict about evidence and not about much else.

At 0d, a patrol stops you with the old words, and you choose:

- **Pay the fine.** Roll your *Coin* — drop 1d first if there's blood on the ledger. Anything stolen is confiscated. The pool clears.
- **Serve the time.** Time passes (below) without a downtime action, and you come out with the pool cleared and nothing in your pockets.
- **Resist arrest.** It's a fight with the *Hold Guards* (Chapter 7), the next pool starts at 4d, and your standing in that hold drops a step (Chapter 9).

A thane's title forgives one arrest. The Thieves Guild can make a ledger disappear for a price. And the next hold over has never heard of you.

*Didact:* `didact do crime jurisdiction='Whiterun Hold'` (`blood`) starts its pool, and rolls it for each crime added to the list; `pool=<it>` rolls it when you show yourself in its towns; at 0d `didact do arrest who=<hero> choice=pay-the-fine` (`stolen=` confiscates what was taken).
