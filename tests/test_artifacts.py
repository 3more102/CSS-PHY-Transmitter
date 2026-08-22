#!/usr/bin/env python3
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def test_required_rtl_modules_exist(self):
        required = {
            "css_phy_tx_top.sv", "css_tx_controller.sv", "payload_ram.sv", "phr_generator.sv",
            "zero_pad_framer.sv", "iq_demux.sv", "symbol_mapper_1m.sv", "symbol_mapper_250k.sv",
            "bit_interleaver.sv", "preamble_sfd_rom.sv", "qpsk_mapper.sv", "dqpsk_encoder.sv",
            "chirp_rom.sv", "csk_modulator.sv", "css_phy_pkg.sv",
        }
        self.assertTrue(required.issubset({p.name for p in (ROOT / "rtl").glob("*.sv")}))

    def test_rom_dimensions_and_binary_widths(self):
        checks = [("codeword_1m.mem",8,4),("codeword_250k.mem",64,32)]
        for m in range(1,5):
            checks.extend([(f"chirp_m{m}_real.mem",152,6),(f"chirp_m{m}_imag.mem",152,6)])
        for name,count,width in checks:
            lines=[x.strip() for x in (ROOT/"rtl"/"rom"/name).read_text().splitlines() if x.strip()]
            self.assertEqual(len(lines),count,name)
            self.assertTrue(all(len(x)==width and set(x)<=set("01") for x in lines),name)

    def test_no_floating_point_or_runtime_trig_in_synth_rtl(self):
        text="\n".join(p.read_text() for p in (ROOT/"rtl").glob("*.sv"))
        self.assertNotRegex(text, r"\$sin\b|\$cos\b")
        # Reject the synthesizable Verilog real data type, but not identifiers
        # such as Tx_real/qpsk_real/chirp_real.
        self.assertNotRegex(text, r"(?m)^\s*real\s+")
        self.assertNotRegex(text, r"#\s*\d+\s*;")

    def test_top_level_required_interface_is_present(self):
        text=(ROOT/"rtl"/"css_phy_tx_top.sv").read_text()
        for name in ("clk","reset","start_Tx","payloadLength","done_Tx","Tx_real","Tx_imag"):
            self.assertRegex(text, rf"\b{re.escape(name)}\b")
        self.assertRegex(text, r"Tx_real\s*,")
        self.assertRegex(text, r"Tx_imag")



    def test_mandatory_demux_is_integrated_not_dead_code(self):
        controller=(ROOT/"rtl"/"css_tx_controller.sv").read_text()
        self.assertRegex(controller, r"\biq_demux\s+u_demux\b")
        self.assertIn(".first_bit(pair_first_raw)", controller)
        self.assertIn(".second_bit(pair_second_raw)", controller)

    def test_vivado_flow_requires_real_target_and_parameterizes_clock(self):
        synth=(ROOT/"scripts"/"vivado_synth.tcl").read_text()
        impl=(ROOT/"scripts"/"vivado_impl.tcl").read_text()
        xdc=(ROOT/"constraints"/"css_phy_tx.xdc").read_text()
        self.assertIn("FPGA_PART is required", synth)
        self.assertIn("FPGA_PART is required", impl)
        self.assertIn("CLOCK_PERIOD_NS", xdc)
        self.assertIn("CLOCK_PORT", xdc)
        self.assertIn("get_clocks -quiet sys_clk", synth)
        self.assertIn("get_clocks -quiet sys_clk", impl)
        self.assertIn("report_timing_summary", synth)
        self.assertIn("report_timing_summary", impl)
        self.assertIn("report_methodology", synth)
        self.assertIn("report_methodology", impl)
        self.assertNotIn("set part xc", synth.lower())

    def test_simulation_only_parameter_guards_are_excluded_from_synthesis(self):
        text=(ROOT/"rtl"/"css_phy_tx_top.sv").read_text()
        self.assertRegex(text, r"`ifndef\s+SYNTHESIS[\s\S]*?\$error[\s\S]*?`endif")


    def test_ci_runs_open_source_hdl_verification_and_preserves_evidence(self):
        workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text()
        self.assertIn("iverilog", workflow)
        self.assertIn("verilator", workflow)
        self.assertIn("make verify", workflow)
        self.assertIn("python3 scripts/require_ci_evidence.py", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("vivado", workflow.lower())
        gate = ROOT / "scripts" / "require_ci_evidence.py"
        self.assertTrue(gate.is_file())
        gate_text = gate.read_text()
        self.assertIn('"RTL simulation regression"', gate_text)
        self.assertIn('"Verilator lint"', gate_text)
        self.assertTrue((ROOT / "requirements.txt").is_file())

    def test_protocol_testbench_covers_invalid_start_busy_start_and_reset_restart(self):
        text=(ROOT/"tb"/"tb_css_phy_protocol.sv").read_text()
        self.assertIn("payloadLength=8'd128", text)
        self.assertIn("start_Tx was accepted while packet active", text)
        self.assertIn("reset did not return transmitter to idle", text)
        self.assertIn("restart sample count", text)

    def test_required_hdl_testbenches_exist(self):
        required={
            "tb_payload_ram.sv","tb_phr_generator.sv","tb_zero_pad_framer.sv","tb_iq_demux.sv",
            "tb_preamble_sfd_rom.sv","tb_symbol_mapper_1m.sv","tb_symbol_mapper_250k.sv",
            "tb_interleaver.sv","tb_qpsk_mapper.sv","tb_dqpsk_encoder.sv","tb_chirp_rom.sv",
            "tb_csk_modulator.sv","tb_css_tx_controller.sv","tb_css_phy_tx_top.sv","tb_css_phy_protocol.sv",
        }
        self.assertTrue(required.issubset({p.name for p in (ROOT/"tb").glob("*.sv")}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
