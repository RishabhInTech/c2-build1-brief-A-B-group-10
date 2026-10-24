# Challenges log · Brief A · Group 10

What broke or surprised us, what we tried, what we changed and why. Entries are dated and written as they happen. A log written on the last evening answers no interview question, and the commit history shows which kind this is.

| # | Phase | What broke or surprised us | What we tried first | What we changed, and why | What we would do differently next time | Who | Date |
|---|---|---|---|---|---|---|---|
| 0 | *Profile and clean* | *Our first join of invoices to payments returned almost no matches.* | *Printed ten ids from each file side by side.* | *Wrote a mapping rule from invoice id to payment reference; kept unmappable rows in a separate list.* | *Profile id formats before writing any join.* | *example* | *example* |
| 1 |profile |Default CSV reading raised UnicodeDecodeError |Read the legacy booking file with the default UTF-8 encoding |Used the starter reader configured for Latin-1 and date parsing |Successfully loaded 19,602 booking-test rows from the selected file |check encoding and datatype before working out  |vysagk/2026-10-24 |


## The entry we are proudest of

<One paragraph on the problem that taught the group the most. This is the story each of you tells in the viva.>
