@{
    ExplorerPython = @{
        Version          = '3.13.15'
        ArchiveName      = 'python-3.13.15-embed-amd64.zip'
        Url              = 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip'
        Hash             = 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'
        InstallDirectory = 'python-3.13.15-explorer'
        Packages = @(
            @{
                Name = 'rdflib'; Version = '7.6.0'
                FileName = 'rdflib-7.6.0-py3-none-any.whl'
                Url = 'https://files.pythonhosted.org/packages/10/c2/6604a71269e0c1bd75656d5a001432d16f2cc5b8c057140ec797155c295e/rdflib-7.6.0-py3-none-any.whl'
                Hash = '30c0a3ebf4c0e09215f066be7246794b6492e054e782d7ac2a34c9f70a15e0dd'
            },
            @{
                Name = 'pyparsing'; Version = '3.1.1'
                FileName = 'pyparsing-3.1.1-py3-none-any.whl'
                Url = 'https://files.pythonhosted.org/packages/39/92/8486ede85fcc088f1b3dba4ce92dd29d126fd96b0008ea213167940a2475/pyparsing-3.1.1-py3-none-any.whl'
                Hash = '32c7c0b711493c72ff18a981d24f28aaf9c1fb7ed5e9667c9e84e3db623bdbfb'
            }
        )
    }
    Node = @{
        Version          = '24.21.0'
        ArchiveName      = 'node-v24.21.0-win-x64.zip'
        Url              = 'https://nodejs.org/dist/v24.21.0/node-v24.21.0-win-x64.zip'
        HashAlgorithm    = 'SHA256'
        Hash             = '158f7685b44de51f6c0df1d153526cbcd3e1bc739a8dfc607721cef75de9e541'
        InstallDirectory = 'node-v24.21.0-win-x64'
    }
    Java = @{
        Version          = '21.0.12+8'
        ArchiveName      = 'OpenJDK21U-jdk_x64_windows_hotspot_21.0.12_8.zip'
        Url              = 'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12%2B8/OpenJDK21U-jdk_x64_windows_hotspot_21.0.12_8.zip'
        HashAlgorithm    = 'SHA256'
        Hash             = '9ba963ee2371874a74185d18bc7bb2ab9407df7683300855ed7606e0662321d0'
        ArchiveRoot      = 'jdk-21.0.12+8'
        InstallDirectory = 'jdk-21.0.12+8'
    }
    NiFi = @{
        Version          = '2.10.0'
        ArchiveName      = 'nifi-2.10.0-bin.zip'
        Url              = 'https://downloads.apache.org/nifi/2.10.0/nifi-2.10.0-bin.zip'
        HashAlgorithm    = 'SHA512'
        Hash             = 'a56c93cad6794beceeaa2e398a2ee9721160acdd16e479050c57879a661024113360c5d5778bcc379c76e6485805869e24cdb534bcf8cb30c6956d09377169d7'
        ArchiveRoot      = 'nifi-2.10.0'
        InstallDirectory = 'nifi-2.10.0'
    }
    Fuseki = @{
        Version          = '6.1.0'
        ArchiveName      = 'apache-jena-fuseki-6.1.0.zip'
        Url              = 'https://downloads.apache.org/jena/binaries/apache-jena-fuseki-6.1.0.zip'
        HashAlgorithm    = 'SHA512'
        Hash             = '1f353ac683e55cb9f4319f1f261ed2a4e59df02c816516e91ccfff69d0818ea6db1b3e2c61eb7ef055499fa72b74ef182e1af731bdf08e1f6d37af795172a543'
        ArchiveRoot      = 'apache-jena-fuseki-6.1.0'
        InstallDirectory = 'apache-jena-fuseki-6.1.0'
    }
    RMLMapper = @{
        Version          = '8.1.0'
        FileName         = 'rmlmapper-8.1.0-r380-all.jar'
        Url              = 'https://github.com/RMLio/rmlmapper-java/releases/download/v8.1.0/rmlmapper-8.1.0-r380-all.jar'
        HashAlgorithm    = 'SHA256'
        Hash             = '819371d49ca47d8ffddae0f34e95f38e8eaaf588ee023e3c2c7527a14d302f58'
        InstallDirectory = 'rmlmapper-8.1.0'
    }
}
