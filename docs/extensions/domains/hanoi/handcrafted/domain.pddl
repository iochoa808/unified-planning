
;; The Towers of Hanoi problem (formalisation by Hector Geffner).

(define (domain hanoi)
    (:requirements :strips :adl)

    (:types
        disc peg - object
    )

    (:predicates
        (on ?x - disc ?y - object)
        (smaller ?x -disc ?y - object)
    )

    (:action move
        :parameters (?d - disc ?from - object ?to - object)
        :precondition (and
            (smaller ?d ?to)
            (on ?d ?from)
            (forall (?w - disc)
                (and
                    (not (on ?w ?d))
                    (not (on ?w ?to))
                )
            )
		)

        :effect (and
            (on ?d ?to)
            (not (on ?d ?from))
		)
    )
)
