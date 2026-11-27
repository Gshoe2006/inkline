# Helping translate Inkline

Inkline is in English, Spanish, French, Brazilian Portuguese, German, Italian and Dutch. The translations were
written without a native speaker, so they're probably understandable but not always natural, and some may be
plain wrong. If you speak one of these languages, you can help a lot by reading through them and suggesting
better wording. You don't need to know any programming.

In Inkline, **Help → Help translate Inkline…** opens this page.

## 1. Get the list of strings

Every string Inkline shows in its window or prints on a page, and the word lists its puzzles use, can be written
out side by side with the English:

- **A web page** (easiest): open it in any browser, search, filter to what still needs review, and type a better
  wording beside any row. It works offline and keeps what you type until you clear it. Then press
  **Copy my suggestions** and paste them into an issue (see step 3).
- **A spreadsheet** (CSV, for Excel, LibreOffice Calc or Google Sheets): fill in the *Better wording* and
  *Comment* columns and attach the file to an issue.

To make them you need Python 3 and a copy of Inkline's source:

```sh
python3 packaging/translation_sheet.py all inkline-review.html        # every language, one web page
python3 packaging/translation_sheet.py fr inkline-fr-review.html      # just French
python3 packaging/translation_sheet.py fr                             # inkline-fr-review.csv
python3 packaging/translation_sheet.py fr --needs-review              # only what nobody has checked, newest first
```

If you can't run these, open a [Suggest a better translation](https://github.com/Gshoe2006/inkline/issues/new?template=translation.yml)
issue saying which language you'd like to check, and a maintainer will attach the page for you.

Each row says **where** the text appears (*window*, *page* — printed on a page — or a puzzle's word list), the
**English**, the **translation**, whether it **needs review**, and a **Key** (the English text, or for word lists
something like `@crossword: Animals`), which is what tells the maintainers exactly which string you mean.

### What "needs review" means

A row marked *needs review* hasn't been checked by a native speaker yet. At the moment that's everything: no
translation has had a native speaker's review so far. The mark says which release the text was written (or last
rewritten) for, such as `6.1.0` or `unreleased`, and `--needs-review` puts the newest first, since those have had
the least use. Once a native speaker has checked a string — whether they changed it or said it's fine — it's
marked as reviewed and the mark goes away.

The marks are kept in [`packaging/translations/review.json`](../packaging/translations/review.json), apart from
the translations themselves.

## 2. What to look for

Read each translation as a parent, teacher or child in your country would. Is it what you'd expect to see in an
app or on a worksheet? Some things to keep in mind:

- **Keep placeholders exactly.** Anything in curly brackets — `{name}`, `{n}`, `{age}` — is filled in by Inkline
  with a number, name or word. Keep each one, spelled exactly as in the English (don't translate `{name}`), but
  move it wherever your language's word order needs it.
- **Menu letters (`&`).** In menu items an `&` goes before the letter you press with Alt to choose it: `&File`
  shows as **F**ile. Keep exactly one `&` in each menu item, before a letter of the word, and make the letters
  different from the other items in the same menu (the Help menu has *What's new*, *Tour of the window*, *Check for
  updates…*, *Check for updates automatically*, *Help translate Inkline…* and *About Inkline*: in French these use
  N, V, M, T, D and P, each once). Only
  menu items have an `&`; elsewhere, write "and".
- **Shortcuts.** Some menu items end in a tab and a shortcut, like `&Copy page⇥Ctrl+C`: keep the tab and the
  shortcut as they are.
- **Length.** Buttons, sidebar labels and menu items have little room: aim for no more than about a third longer
  than the English, and shorter is better. A long label wraps or is cut off, especially on a phone. Printed titles
  and instructions have more room but should still fit on one or two lines. If the only good translation is much
  longer, say so in the comment and the maintainers will check it fits.
- **Formal or informal.** The translations use the informal form throughout (*tú*, *tu*, *du*, *jij*…), in the
  window and on printed pages, which children read. Keep to it unless it really sounds wrong, and say why.
- **Consistency.** The same thing should have the same name everywhere ("booklet", "pattern", "answer pages").
  The search box on the web page helps check.
- **The same language variety.** Portuguese is Brazilian Portuguese. For Spanish, French and the others, use
  wording that works across countries where you can, and say in a comment if a word is only used in one country.

### Word lists for puzzles

The word search themes, crossword words and clues, the logic puzzle's names and things, the cryptogram's sayings,
the word ladder's words and the handwriting words are written in each language rather than translated from
English. They're printed for children to solve, so:

- **Real, common words that a child would know**, spelled the usual way. No rare, adult, rude or upsetting words,
  no brand names. Clues should be short and simple.
- **Letters**: puzzle grids drop accents (É → E), except Spanish Ñ, and German writes Ä Ö Ü as AE OE UE and ß as
  SS. A word that's ambiguous without its accent may be a poor choice.
- **Lengths**: word search words of up to 8 letters fit every grid (longer words only appear in the bigger ones);
  crossword answers are at most 15 letters; cryptogram sayings at most 120 characters; ladder words are three,
  four or five letters, and every step of a ladder must be a real word, so a list with lots of words one letter
  apart works best.
- **Names** in the logic puzzle should be common children's first names in your language's countries, short and
  easy to tell apart.

## 3. Suggest changes

**With an issue** (no programming needed): open a
[Suggest a better translation](https://github.com/Gshoe2006/inkline/issues/new?template=translation.yml) issue.
Fill in one suggestion — language, where it appears, what it says now, what it should say and why — or paste
several rows from the web page's **Copy my suggestions** into the last box. You can also attach a filled-in
spreadsheet. If you checked a lot of strings and found them fine, say which (for example "all of the Help menu"
or "every row in the attached sheet"): that's just as useful, since they can then be marked as reviewed.

**With a pull request**: edit `inkengine/locale/<code>.json` (the English text is the key; change only the text
after the colon), and in `packaging/translations/review.json` move each string you checked from `needs_review` to
`reviewed` for your language, with the date. Keep the files sorted and indented as they are: the easiest way is to
write your changes as a CSV and let `apply.py` (below) make the edit. Word lists are in
`inkengine/patterns/words.py`, `crossword.py`, `logic.py`, `cryptogram.py`, `ladder.py` and `trace.py`.

## 4. For maintainers: applying suggestions

`packaging/translations/apply.py` takes a CSV, checks every row, updates the translation files and marks the
strings as reviewed:

```sh
python3 packaging/translations/apply.py suggestions.csv --dry-run          # what would change
python3 packaging/translations/apply.py suggestions.csv --note "issue #140"
python3 packaging/translations/apply.py inkline-fr-review.csv --all-checked   # a sheet whose every row was read
```

It reads either the lines from **Copy my suggestions** or the issue form (`key,language,new_text`, optionally
`current_text,comment`; an empty `new_text` means "checked, fine as it is") or a filled-in review sheet (each row
with a *Better wording*; with `--all-checked` the other rows count as checked too). A new text must keep the
English's placeholders, its `&` (or lack of one) and its tab; if any row fails, nothing is written. The JSON files
are rewritten exactly as they're kept (sorted keys, one space of indent, accents as they are), so `git diff` shows
only the strings that changed. Suggestions for word lists are printed for editing by hand; once edited, confirm
them with a line such as `@crossword: Animals,fr,` (empty `new_text`).

`python3 packaging/translations/review.py` says how many strings in each language still need review, and
`--sync` marks strings added since (which count as needing review anyway) and drops strings that no longer
exist. Accelerator letters aren't checked automatically: when applying menu items, look at the other items in
the same menu.

When adding a new string in English, add its translations to all six files as before; it counts as needing review
until someone checks it, with no change to `review.json` needed (run `review.py --sync` to record when it was
written).
