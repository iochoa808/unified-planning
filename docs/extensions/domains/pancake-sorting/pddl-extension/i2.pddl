; Multi-step instance (original from user).
; One solution: flip(4) -> (3 1 2 4 5... wait, recalculate)
; (4 5 2 1 3): flip(1) -> (5 4 2 1 3), flip(4) -> (3 1 2 4 5), ...
; Requires several flips.
(define (problem pancake_i2)
  (:domain pancake)
  (:init
      (= (pancake_stack) (array.mk (4 5 2 1 3)))
  )
  (:goal
      (= (pancake_stack) (array.mk (1 2 3 4 5)))
  )
)
