; Reversed stack: one flip solves it.
; flip(4) reverses positions 0-4: (5 4 3 2 1) -> (1 2 3 4 5)
(define (problem pancake_i3)
  (:domain pancake)
  (:init
      (= (pancake_stack) (array.mk (5 4 3 2 1)))
  )
  (:goal
      (= (pancake_stack) (array.mk (1 2 3 4 5)))
  )
)
