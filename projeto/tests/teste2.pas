program Teste2;
var
  contador1, contador2: integer;
begin
  contador1 := 0;

  while contador1 < 5 do
  begin
    writeln('Iteraçao do ciclo while: ');
    writeln(contador1);
    contador1 := contador1 + 1;

    contador2 := 0;
    repeat
      writeln('  Ciclo repeat aninhado: ');
      writeln(contador2);
      contador2 := contador2 + 1;
    until contador2 = 3;
  end;
end.
