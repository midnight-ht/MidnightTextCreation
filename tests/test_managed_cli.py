import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path
from tests.test_content_manager import config

class ManagedCliTests(unittest.TestCase):
    def test_cli_binding_writes_to_account_directory_and_retains_old_output_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            cfg=root/'accounts.json';cfg.write_text(json.dumps(config(root)),encoding='utf-8')
            inp=root/'input.json';inp.write_text(json.dumps({'title':'标题','raw_material':'正文'}),encoding='utf-8')
            output=root/'output.json'
            run=subprocess.run([sys.executable,'-m','scripts.run_skill',str(inp),'--account-config',str(cfg),'--binding','wa','--data-dir',str(root/'data'),'--json-out',str(output)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['execution_mode'],'local_deterministic')
            self.assertEqual(result['status'],'needs_human_review')
            self.assertEqual(result['final_text'],'正文')
            self.assertEqual(result['managed_content']['binding_id'],'wa')
            self.assertTrue(Path(result['managed_content']['directory'],'publication.json').is_file())

if __name__=='__main__':unittest.main()
