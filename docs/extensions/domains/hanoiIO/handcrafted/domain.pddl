(define (domain hanoi_5)

    (:requirements :typing :arrays)

    (:types
        peg   - object
        range - (number 0 5)
        stack - (array 5 range)
    )

    (:functions
        (tower ?p - peg) - stack
        (top   ?p - peg) - range
    )

    (:action move
        :parameters (?from ?to - peg ?f ?t - range)
        :precondition (and
            (not (= ?from ?to))

            ; bind ?f and ?t to the actual top positions
            (= (top ?from) ?f)
            (= (top ?to)   ?t)

            ; ?from is not empty
            (> ?f 0)

            ; ?to is empty or top disc of ?from is smaller
            (or
            (= ?t 0)
                (<
                    (read (tower ?from) ?f)
                    (read (tower ?to)   ?t))
            )
        )
        :effect (and
            ; place disc on ?to
            (write ((tower ?to)   (+ ?t 1)) (read (tower ?from) ?f))
            ; clear slot on ?from
            (write ((tower ?from) ?f)       0)
            ; update counters
            (assign (top ?from) (- ?f 1))
            (assign (top ?to)   (+ ?t 1))
        )
  )
)