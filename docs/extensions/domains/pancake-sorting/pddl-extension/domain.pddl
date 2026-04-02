(define (domain pancake)

    (:requirements :typing :arrays :bounded-integers)

    (:types
        idx     - (number 0 4)    ; array positions 0..4
        pancake - (number 1 5)    ; pancake sizes 1 (smallest) .. 5 (largest)
        stack   - (array 5 pancake)
    )

    (:functions
        (pancake_stack) - stack
    )

    ; Flip the prefix of the stack ending at position ?f (0-indexed).
    ; Position ?i (for ?i <= ?f) receives the value that was at position (?f - ?i),
    ; reversing the prefix.  All reads use the state before the action, so
    ; simultaneous assignment is correct even when ?i and (?f - ?i) overlap.
    (:action flip
        :parameters (?f - idx)
        :precondition ()
        :effect (and
            (forall (?i - idx)
                (when (<= ?i ?f)
                    (write (pancake_stack) (?i) (read (pancake_stack) (- ?f ?i)))
                )
            )
        )
    )
)
