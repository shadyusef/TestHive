# Shared by the demos (sourced, not run). A demo works in a throw-away copy of the tool that is removed when it ends;
# TH_KEEP_DEMO=1 keeps the folder to look around afterwards.
#   demo_copy [tar --exclude options...]   copies the tool from $SRC into a new temporary folder $W and enters it
#   drop_files <name>...                    removes the project's own top-level files from the copy, by full path
# The owner's private files (.env, masking lists and map, .private-names, HANDOVER.md) never stay in a copy.
demo_cleanup() {
  set +e; cd / || return
  for p in $(jobs -p); do  # a Studio started with & : give it time to close after /api/shutdown, then stop it
    for i in $(seq 1 30); do kill -0 "$p" 2>/dev/null || break; sleep 0.5; done; kill "$p" 2>/dev/null || true
  done
  if [ -n "$TH_KEEP_DEMO" ]; then echo "Demo folder kept: $W"; return; fi
  for i in 1 2 3 4 5; do rm -rf "$W" 2>/dev/null; [ -d "$W" ] || return 0; sleep 1; done  # Windows: a Studio still closing holds the folder
}
demo_copy() {
  W=$(mktemp -d); trap demo_cleanup EXIT
  export TH_STUDIO_CONFIG="$W/.studio.json"  # the demo's Studio does not add its throw-away folder to your recent projects
  (cd "$SRC" && tar --exclude=.git --exclude='./runs/R-*' --exclude=./runs/agents --exclude='./demo/*/output' "$@" -cf - .) | (cd "$W" && tar -xf -)
  drop_files .env .mask-terms .mask-allow .mask-map.json .private-names HANDOVER.md
  cd "$W"
}
drop_files() {  # full paths: a tar --exclude=./NAME would also drop templates/NAME on macOS
  for f in "$@"; do rm -f "$W/$f"; done
}
