func print_int(n int);
func print_str(s string);
func read_int() int;

func main(){
  var arr [10]int;
  arr[2] = read_int();
  print_int(arr[2]);

}
