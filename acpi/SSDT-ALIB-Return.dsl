DefinitionBlock ("", "SSDT", 2, "CDEX", "ALIBRET", 0x00000001)
{
    External (\_SB.X026, MethodObj)
    Scope (\_SB)
    {
        Method (A026, 1, NotSerialized)
        {
            X026 (Arg0)
            Return (Zero)
        }
    }
}
