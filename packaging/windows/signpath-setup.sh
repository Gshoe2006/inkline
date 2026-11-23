#!/usr/bin/env bash
# Connects Inkline's release workflow to SignPath, once SignPath Foundation has accepted the project
# (docs/code-signing.md). Run it on your own computer, from anywhere, with the GitHub CLI signed in:
#
#     bash packaging/windows/signpath-setup.sh            set it up (asks for the organization ID and API token)
#     bash packaging/windows/signpath-setup.sh --check    show what's set up, change nothing
#     bash packaging/windows/signpath-setup.sh --remove   stop signing: releases go out unsigned again
#
# It stores the API token as the repository secret SIGNPATH_API_TOKEN and the organization ID as the
# variable SIGNPATH_ORGANIZATION_ID (plus SIGNPATH_PROJECT_SLUG / SIGNPATH_SIGNING_POLICY_SLUG if yours aren't
# the defaults, inkline and release-signing). The token goes straight to GitHub, encrypted: it isn't shown,
# written to a file or kept in your shell history.
set -euo pipefail

REPO="${INKLINE_REPO:-Gshoe2006/inkline}"
DEFAULT_PROJECT=inkline
DEFAULT_POLICY=release-signing

say() { printf '%s\n' "$*"; }
fail() { printf 'signpath-setup: %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null 2>&1 || fail "the GitHub CLI (gh) isn't installed: see https://cli.github.com, then run 'gh auth login'."
gh auth status >/dev/null 2>&1 || fail "the GitHub CLI isn't signed in: run 'gh auth login' first."

admin=$(gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null) || fail "can't read $REPO with your GitHub sign-in."
[ "$admin" = true ] || fail "your GitHub account can't change $REPO's settings (it needs admin access)."

two_factor() {
    # SignPath Foundation requires two-factor authentication on GitHub (and on SignPath)
    case "$(gh api user --jq '.two_factor_authentication' 2>/dev/null || true)" in
        true) say "Two-factor authentication on GitHub: on." ;;
        false) say "Two-factor authentication on GitHub: OFF. SignPath Foundation requires it:"
               say "  turn it on at https://github.com/settings/security" ;;
        *) say "Two-factor authentication on GitHub: couldn't tell (check https://github.com/settings/security)." ;;
    esac
}

show() {
    say "Repository: $REPO"
    two_factor
    local vars secrets
    vars=$(gh variable list --repo "$REPO" 2>/dev/null | awk '{print $1}' | grep '^SIGNPATH_' || true)
    secrets=$(gh secret list --repo "$REPO" 2>/dev/null | awk '{print $1}' | grep '^SIGNPATH_' || true)
    if printf '%s\n' "$vars" | grep -qx SIGNPATH_ORGANIZATION_ID && printf '%s\n' "$secrets" | grep -qx SIGNPATH_API_TOKEN; then
        say "Signing: set up. The next release waits for you to approve it in SignPath."
    else
        say "Signing: not set up. Releases go out unsigned."
    fi
    for v in SIGNPATH_ORGANIZATION_ID SIGNPATH_PROJECT_SLUG SIGNPATH_SIGNING_POLICY_SLUG; do
        if printf '%s\n' "$vars" | grep -qx "$v"; then
            say "  variable $v = $(gh variable get "$v" --repo "$REPO")"
        fi
    done
    if printf '%s\n' "$secrets" | grep -qx SIGNPATH_API_TOKEN; then
        say "  secret SIGNPATH_API_TOKEN is set (GitHub never shows its value)"
    fi
}

case "${1:-}" in
    --check) show; exit 0 ;;
    --remove)
        printf 'Stop signing %s releases? [y/N] ' "$REPO"
        read -r yes
        case "$yes" in [yY]*) ;; *) say "Nothing changed."; exit 0 ;; esac
        gh secret delete SIGNPATH_API_TOKEN --repo "$REPO" 2>/dev/null || true
        for v in SIGNPATH_ORGANIZATION_ID SIGNPATH_PROJECT_SLUG SIGNPATH_SIGNING_POLICY_SLUG; do
            gh variable delete "$v" --repo "$REPO" 2>/dev/null || true
        done
        say "Removed. Releases go out unsigned again."
        exit 0 ;;
    "") ;;
    *) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

say "Connecting $REPO's releases to SignPath."
two_factor
say ""
say "From SignPath (https://app.signpath.io):"

org=""
while :; do
    printf 'Organization ID (under your organization'"'"'s settings, like 1a2b3c4d-...): '
    read -r org
    org=$(printf '%s' "$org" | tr -d '[:space:]')
    if printf '%s' "$org" | grep -Eqi '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
        break
    fi
    say "  That doesn't look like an organization ID (a GUID such as 1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d)."
done

printf 'Project slug [%s]: ' "$DEFAULT_PROJECT"
read -r project
project=$(printf '%s' "${project:-$DEFAULT_PROJECT}" | tr -d '[:space:]')
printf 'Signing policy slug [%s]: ' "$DEFAULT_POLICY"
read -r policy
policy=$(printf '%s' "${policy:-$DEFAULT_POLICY}" | tr -d '[:space:]')

token=""
while [ -z "$token" ]; do
    printf 'API token (it won'"'"'t show as you paste it): '
    read -rs token
    say ""
    token=$(printf '%s' "$token" | tr -d '[:space:]')
done

printf '%s' "$token" | gh secret set SIGNPATH_API_TOKEN --repo "$REPO" >/dev/null
unset token
gh variable set SIGNPATH_ORGANIZATION_ID --repo "$REPO" --body "$org" >/dev/null
# the workflow uses the defaults when these aren't set
if [ "$project" != "$DEFAULT_PROJECT" ]; then
    gh variable set SIGNPATH_PROJECT_SLUG --repo "$REPO" --body "$project" >/dev/null
else
    gh variable delete SIGNPATH_PROJECT_SLUG --repo "$REPO" >/dev/null 2>&1 || true
fi
if [ "$policy" != "$DEFAULT_POLICY" ]; then
    gh variable set SIGNPATH_SIGNING_POLICY_SLUG --repo "$REPO" --body "$policy" >/dev/null
else
    gh variable delete SIGNPATH_SIGNING_POLICY_SLUG --repo "$REPO" >/dev/null 2>&1 || true
fi

say ""
show
say ""
say "Done. When the next release merges, approve its signing request in SignPath within 75 minutes."
