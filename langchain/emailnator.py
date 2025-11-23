import asyncio
import perplexity_async

emailnator_cookies = {
    '_ga': 'GA1.1.1451209083.1763897293',
    '__gads': 'ID=69bd6bea0e742b57:T=1763897294:RT=1763897294:S=ALNI_MZ3eUp65P67YJJu-eiAElM1mNYEvw',
    '__gpi': 'UID=000012a846699de3:T=1763897294:RT=1763897294:S=ALNI_Ma9gaOYA-iCFzsMqkf3Q5i2ZrDTnw',
    '__eoi': 'ID=a726fc64031bc517:T=1763897294:RT=1763897294:S=AA-AfjafNOPcsPmOrXA9u-x0Ru9V',
    'FCNEC': '%5B%5B%22AKsRol9uNrlO_--SBu1OM0cAz-iriDnD4zrFF0s1PYeXZt_fWWMwgR65qhNBHCIlZ2uV5x5KTJYGM29Z9gD4Np7pnuVLR_0E7Ut3eNf8QHCNVbLC5ACYj5B_bdUEIoJPHifUQLE--qLv9nqrk-AmAszmJ7Bj2XCZxQ%3D%3D%22%5D%5D',
    'XSRF-TOKEN': 'eyJpdiI6Ijd5V2xodjF2K0tUb2l0WUIxamU5aHc9PSIsInZhbHVlIjoiTVFGWmtOUmcramZGTTA2NzcwaWo0a3JzR1JYdnh4RUFVMnJpdjZDQ3FSUkpwdGlvcnVVT2k5QUpoL2dETXg3MERRajZxQURiL1pGWWE2ZjFlVHlxbXU4b3NHNWdXZjEzS3VxSDl3Z3lRZ1dIbS9zZ1VrRlBnWU1Sdjh5V0lSbXkiLCJtYWMiOiIxMjIyNmVhMDU4MGQyNDgwODM1NGJkNDNlOTVhNDFiZWQ1Njc4NzhkOGVlNjA1OGU0OTk2MWZjMjg0M2Y0ZWU5IiwidGFnIjoiIn0%3D',
    'gmailnator_session': 'eyJpdiI6IlM4SFh5UVdFVzB6KzV2ZE1TWXF4VUE9PSIsInZhbHVlIjoiYWpHRjlUa3VZK3JvNmRPVlZhN3k4ZmRpUVd6clJ4WmJ2UDd5NWRGUHFpQ2ZUVFNQS1J6djYvcDdkZ1gwQmwwcFlBM0ZtSTFzQjZmeDFPRm9aQWUzWkdLaE5Fd21JdWljQWlRQTVEY1NzYm5rWVJYRzZYeGhOR2dlaUJ1MXRMMVUiLCJtYWMiOiJjM2I1YzZmZGQ4ZjQwNzkwZDU4Y2NiMTUxNjRjZjBkM2FkNGY2NzlhYzhjZjYxYjNiNmRkNGE4MWJlZGRjOTI1IiwidGFnIjoiIn0%3D',
    '_ga_6R52Y0NSMR': 'GS2.1.s1763897293$o1$g1$t1763897375$j46$l0$h0',
    'FCCDCF': '%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B32%2C%22%5B%5C%22e71843fc-a995-456a-9ffc-2e13aba86d60%5C%22%2C%5B1763897291%2C68000000%5D%5D%22%5D%5D%5D',
}

async def test():
    perplexity_cli = await perplexity_async.Client()
    await perplexity_cli.create_account(emailnator_cookies) # Creates a new gmail, so your 5 pro queries will be renewed.

    resp = await perplexity_cli.search('bisa kasih tau codenya apa ya??', mode='reasoning', model='gpt-5.1-thingking', sources=['web'], files={'myfile.txt': open('file.txt').read()}, stream=False, language='en-US', follow_up=None, incognito=False)
    print(resp)

asyncio.run(test())