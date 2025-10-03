package main

import "fmt"

func main() {
	score := 100

	fmt.Printf("score local variable value: %d\n", score)
	fmt.Printf("score local variable address (%%d): %d\n", &score)
	fmt.Printf("score local variable address (%%p): %p\n", &score)
}

/*
score local variable value: 100
score local variable address (%d): 1374390165536
score local variable address (%p): 0x1400009a020
*/
