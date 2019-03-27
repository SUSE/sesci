### BEGIN OF FILE snippets/deepsea-trigger.bash ###

function parse_comment_help() {
    echo "Usage: @susebot run teuthology [[with|for] [suite] SUITE] [using|via SUITE_BRANCH] [against ARTIFACT_LABEL] [on SITE]"
}
function parse_comment() {
    local comment="$1"
    x="^\s*@susebot\s+run\s+teuthology\
(\s+((with|for)\s+)?(suite\s+)?(\S+))?\
(\s+(using|via)\s+(\S+))?\
(\s+(against)\s+(\S+))?\
(\s+(on)\s+(\S+))?\
\s*\$"
    if [[ "$comment" =~ $x ]] ; then
        # with|for suite <suite>
        local suite="${BASH_REMATCH[5]}"
        [[ "$suite" ]] && {
            echo "Detected phrase '${BASH_REMATCH[3]} ${BASH_REMATCH[5]}'" > /dev/stderr
            export SUITE="$suite"
        }
        # using|via suite_branch
        local branch="${BASH_REMATCH[8]}"
        [[ "$branch" ]] && {
            echo "Detected phrase '${BASH_REMATCH[7]} ${BASH_REMATCH[8]}'" > /dev/stderr
            export SUITE_BRANCH="$branch"
        }
        # against artifact_label
        local artifact=${BASH_REMATCH[11]}
        [[ "$artifact" ]] && {
            echo "Detected phrase '${BASH_REMATCH[10]} ${BASH_REMATCH[11]}'" > /dev/stderr
        }
        # on site
        local site="${BASH_REMATCH[14]}"
        [[ "$site" ]] && {
            echo "Detected phrase '${BASH_REMATCH[13]} ${site}'" > /dev/stderr
            export SITE="$site"
        }
    else
        echo "Comment: $comment" > /dev/stderr
        echo "Does not match the regex: $x" > /dev/stderr
    fi
}

### END OF FILE snippets/deepsea-trigger.bash ###
