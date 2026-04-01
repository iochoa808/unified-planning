(define (problem hanoi_5)
    (:domain hanoi)

    (:objects
        peg1 peg2 peg3 - peg
    )

    (:init
        (= (top peg1) 5)
        (= (top peg2) 0)
        (= (top peg3) 0)

        (= (tower peg1) (array.mk (1 2 3 4 5)))
        (= (tower peg2) (array.mk (0 0 0 0 0)))
        (= (tower peg3) (array.mk (0 0 0 0 0)))
    )

    (:goal
        (and
            (= (tower peg3) (array.mk (1 2 3 4 5)))
            (= (top peg3) 5)
        )
    )
)
