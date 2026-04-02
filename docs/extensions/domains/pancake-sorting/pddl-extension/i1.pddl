; One flip solves it.
; flip(2) reverses positions 0-2: (3 2 1 4 5) -> (1 2 3 4 5)
(define (problem pancake_i1)
  (:domain pancake)
  (:init
      (= (pancake_stack) (array.mk (3 2 1 4 5)))
  )
  (:goal
      (= (pancake_stack) (array.mk (1 2 3 4 5)))
  )
)
