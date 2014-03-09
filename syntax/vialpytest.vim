syntax keyword pytestOk PASS
syntax keyword pytestFail ERROR FAIL FAILED_COLLECT
syntax keyword pytestSkip SKIP

hi link pytestOk DiffAdd
hi link pytestFail DiffDelete
hi link pytestSkip DiffChange
